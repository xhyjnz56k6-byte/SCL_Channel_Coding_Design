#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def run(command: list[object], cwd: Path) -> None:
    print("+", " ".join(str(item) for item in command), flush=True)
    subprocess.run([str(item) for item in command], cwd=cwd, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check_plot_manifest(path: Path) -> int:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for fig in manifest["figures"]:
        data = path.parent / fig["figureDataCsv"]
        png = path.parent / fig["png"]
        if sha(data) != fig["figureDataSha256"]:
            raise RuntimeError(f"figure-data hash mismatch: {data}")
        if png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha(png) != fig["pngSha256"]:
            raise RuntimeError(f"PNG hash mismatch: {png}")
        count += 1
    return count


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    s3 = stage.parent
    results = stage / "results"
    results.mkdir(parents=True, exist_ok=True)

    run([sys.executable, stage / "scripts" / "revision_postprocess.py"], repo)
    run([sys.executable, s3 / "stage10_traceback_study/scripts/check_stage10.py"], repo)
    run([sys.executable, s3 / "stage11_soft_quantization/scripts/check_stage11.py"], repo)
    run([sys.executable, s3 / "stage13_sliding_window_viterbi/scripts/check_stage13.py"], repo)
    run([sys.executable, s3 / "stage14_block_continuous_comparison/scripts/check_stage14.py"], repo)
    run([sys.executable, s3 / "stage12_continuous_encoder/scripts/run_stage12.py"], repo)
    run(["git", "diff", "--check"], repo)

    readmes = sorted(s3.glob("stage*_*/readme.txt"))
    if len(readmes) != 15:
        raise RuntimeError(f"expected 15 readme.txt files, got {len(readmes)}")
    coarse = read_csv(s3 / "stage09_awgn_formal/results/stage09_two_level_coarse_point_results.csv")
    dense = read_csv(s3 / "stage09_awgn_formal/results/stage09_two_level_dense_point_results.csv")
    merged = read_csv(s3 / "stage09_awgn_formal/results/stage09_two_level_merged_point_results.csv")
    if len(coarse) != 186 or len(dense) != 126 or len(merged) < 186:
        raise RuntimeError("Stage09 two-level row coverage failed")
    for row in coarse + dense + merged:
        for field in ("snrDb", "esN0Db", "ebN0Db", "actualRate", "sigmaSquared",
                      "berCiLow", "berCiHigh", "ferCiLow", "ferCiHigh"):
            if field not in row or row[field] == "":
                raise RuntimeError(f"Stage09 missing field {field}")

    plot_counts = {
        "stage09": check_plot_manifest(s3 / "stage09_awgn_formal/results/stage09_two_level_plot_manifest.json"),
        "stage10": check_plot_manifest(s3 / "stage10_traceback_study/results/stage10_traceback_plot_manifest.json"),
        "stage11": check_plot_manifest(s3 / "stage11_soft_quantization/results/stage11_quantization_plot_manifest.json"),
        "stage13": check_plot_manifest(s3 / "stage13_sliding_window_viterbi/results/stage13_window_plot_manifest.json"),
        "stage14": check_plot_manifest(s3 / "stage14_block_continuous_comparison/results/stage14_compare_plot_manifest.json"),
        "stage15": check_plot_manifest(results / "stage15_final_plot_manifest.json"),
    }
    expected_counts = {"stage09": 5, "stage10": 4, "stage11": 5, "stage13": 6, "stage14": 6, "stage15": 3}
    if plot_counts != expected_counts:
        raise RuntimeError(f"plot count mismatch: {plot_counts}")

    gate_rows = [
        {"stage": "Stage01-15 readme", "status": "PASS", "detail": "15 Chinese readme.txt files"},
        {"stage": "Stage09 two-level grid", "status": "PASS", "detail": f"coarse={len(coarse)}, dense={len(dense)}, merged={len(merged)}"},
        {"stage": "Stage10 traceback", "status": "PASS", "detail": "Dtb=35/49/70/84/98/112, 4 plots"},
        {"stage": "Stage11 quantization", "status": "PASS", "detail": "Float/Q3/Q4/Q6, 5 plots"},
        {"stage": "Stage12 regression", "status": "PASS", "detail": "continuous encoder regression rerun"},
        {"stage": "Stage13 true sliding window", "status": "PASS", "detail": "W/S/D parameter matrix, 6 plots"},
        {"stage": "Stage14 independent schemes", "status": "PASS", "detail": "A/B/C/D independent execution, 6 plots"},
        {"stage": "Stage15 final integration", "status": "PASS", "detail": "3 plots, core questions, figure guide"},
    ]
    write_csv(results / "stage15_cc_s3_revision_gate_matrix.csv", gate_rows)
    index_rows = []
    for path in [
        s3 / "stage09_awgn_formal/results/stage09_two_level_merged_point_results.csv",
        s3 / "stage09_awgn_formal/results/stage09_two_level_report.md",
        s3 / "stage10_traceback_study/results/stage10_traceback_recommendation.csv",
        s3 / "stage11_soft_quantization/results/stage11_quantization_recommendation.csv",
        s3 / "stage13_sliding_window_viterbi/results/stage13_sliding_window_results.csv",
        s3 / "stage14_block_continuous_comparison/results/stage14_block_continuous_results.csv",
        results / "stage15_core_questions_answer.md",
        results / "stage15_all_figures_guide.md",
        results / "stage15_final_summary_report.md",
    ]:
        index_rows.append({
            "path": path.relative_to(repo).as_posix(),
            "sha256": sha(path),
            "sizeBytes": path.stat().st_size,
        })
    write_csv(results / "stage15_cc_s3_revision_result_index.csv", index_rows)
    print("PASS_CC_S3_INTEGRATION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
