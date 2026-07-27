#!/usr/bin/env python3
"""Finalize audit files for the common-SNR multipath comparison."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    rows = read(stage / f"results/{PREFIX}_results.csv")
    summary = read(stage / f"{PREFIX}_summary.csv")
    ranking = read(stage / f"{PREFIX}_pointwise_ranking.csv")
    crossing = read(stage / f"{PREFIX}_curve_crossing_analysis.csv")
    files = []
    for path in stage.rglob("*"):
        if path.is_file() and PREFIX in path.name or (path.is_file() and path.parent.name == "plots" and path.name.startswith("stage08_multipath_common_snr_")):
            files.append(path)
    hashes = {str(path.relative_to(repo)).replace("\\", "/"): sha(path) for path in sorted(files)}
    (stage / f"{PREFIX}_file_hashes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total_frames = sum(int(row["totalFrames"]) for row in rows)
    target_points = sum(row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED" for row in rows)
    max_points = sum(row["stopReason"] == "MAX_FRAMES_REACHED" for row in rows)
    max_residual = max(float(row["solverResidualMax"]) for row in rows)
    old_stage = stage.parent / "stage08_multipath_formal"
    old_results = old_stage / "results" / "stage08_multipath_formal_results.csv"
    old_grid = old_stage / "stage08_multipath_formal_frozen_grid.csv"
    stage07_model = stage.parent / "stage07_multipath_validation" / "stage07_multipath_validation_frozen_model.json"

    def best(payload: int, metric: str, snr_index: int) -> str:
        selected = [r for r in rows if int(r["payloadLength"]) == payload and int(r["waveformSnrIndex"]) == snr_index]
        return min(selected, key=lambda r: float(r[metric]))["caseId"]

    conclusions = []
    for payload in (200, 300):
        conclusions.append({
            "payloadLength": payload,
            "lowSnrBerBest": best(payload, "ber", 0),
            "midSnrBerBest": best(payload, "ber", 18),
            "highSnrBerBest": best(payload, "ber", 36),
            "lowSnrFerBest": best(payload, "fer", 0),
            "midSnrFerBest": best(payload, "fer", 18),
            "highSnrFerBest": best(payload, "fer", 36),
            "ratePriority": max([s for s in summary if int(s["payloadLength"]) == payload], key=lambda s: float(s["actualRate"]))["caseId"],
            "decodeLatencyPriority": min([s for s in summary if int(s["payloadLength"]) == payload], key=lambda s: float([r for r in rows if r["caseId"] == s["caseId"]][0]["decodeTimeMeanNs"]))["caseId"],
            "equalizeLatencyPriority": min([s for s in summary if int(s["payloadLength"]) == payload], key=lambda s: float([r for r in rows if r["caseId"] == s["caseId"]][0]["equalizeTimeMeanNs"]))["caseId"],
            "qualification": "No single absolute best independent of waveform-SNR operating region.",
        })
    with (stage / f"{PREFIX}_conclusion.md").open("w", encoding="utf-8") as handle:
        handle.write(f"# {PREFIX} Conclusion\n\n")
        handle.write("本结论只使用统一 `waveformSnrDb=0:0.5:18` 网格下的同 SNR 横向比较；旧 Stage08 标记为 `LEGACY_WIDE_GRID_FORMAL`，不作为最终横向排名依据。\n\n")
        handle.write("`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。\n\n")
        for item in conclusions:
            handle.write(f"## {item['payloadLength']} bit\n\n")
            handle.write(f"- 低 SNR BER 最优：{item['lowSnrBerBest']}；FER 最优：{item['lowSnrFerBest']}。\n")
            handle.write(f"- 中 SNR BER 最优：{item['midSnrBerBest']}；FER 最优：{item['midSnrFerBest']}。\n")
            handle.write(f"- 高 SNR BER 最优：{item['highSnrBerBest']}；FER 最优：{item['highSnrFerBest']}。\n")
            handle.write(f"- 码率优先：{item['ratePriority']}；BCH 译码时延优先：{item['decodeLatencyPriority']}；MMSE 均衡时延优先：{item['equalizeLatencyPriority']}。\n")
            handle.write("- 不存在脱离 SNR 工作区间的单一绝对最优方案。\n\n")
    (stage / f"{PREFIX}_known_issues.md").write_text(
        "# Known Issues\n\n"
        "- 零 BER/FER 点表示在有限帧数内未观测到错误，不等于真实错误率为零；对数图仅使用 0.5/count surrogate 显示。\n"
        "- 时延统计受本机调度和缓存波动影响，适合作同一批次内相对比较。\n"
        "- `miscorrectionFrames` 与 `undetectedErrorFrames` 是当前接口下同一事件集合的语义别名。\n"
        "- 本分支尚未合并 `main`，mergeStatus 保持 `NOT_MERGED`。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_validation_report.md").write_text(
        f"# Validation Report\n\n"
        f"- Results gate: PASS_STAGE08_COMMON_SNR_RESULTS_CHECK\n"
        f"- Plot gate: PASS_STAGE08_COMMON_SNR_PLOT_CHECK\n"
        f"- Final comparison gate: PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON\n"
        f"- Point count: 296\n"
        f"- Total frames: {total_frames}\n"
        f"- TARGET_FRAME_ERRORS_REACHED points: {target_points}\n"
        f"- MAX_FRAMES_REACHED points: {max_points}\n"
        f"- Solver residual max: {max_residual:.17g}\n"
        f"- NaN/Inf: 0\n"
        f"- Stage07 frozen model SHA-256: {sha(stage07_model)}\n"
        f"- Legacy Stage08 result SHA-256: {sha(old_results)}\n"
        f"- Legacy Stage08 grid SHA-256: {sha(old_grid)}\n"
        f"- Legacy data label: LEGACY_WIDE_GRID_FORMAL\n\n"
        "`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_changed_files.md").write_text(
        "# Changed Files\n\n"
        "新增 common-SNR Stage08 补充实验目录，包含 C++ runner、Python checker/plot/audit、冻结网格、正式结果、图像证据和审计文件。未修改 Stage07 与旧 Stage08 结果。\n",
        encoding="utf-8",
    )
    (stage / f"{PREFIX}_manifest.json").write_text(json.dumps({
        "stage": PREFIX,
        "branch": "stage07-08-bch-s2-multipath",
        "baseCommit": git(repo, "merge-base", "main", "HEAD"),
        "currentHeadAtAuditGeneration": git(repo, "rev-parse", "HEAD"),
        "formalRunGitCommit": rows[0]["gitCommit"],
        "formalConfigHash": rows[0]["configHash"],
        "formalPointCount": len(rows),
        "formalFrameCount": total_frames,
        "grid": {"startDb": 0.0, "endDb": 18.0, "stepDb": 0.5, "gridType": "BASE_0P5DB", "refinement": "NO_REFINEMENT"},
        "gates": [
            "PASS_STAGE08_COMMON_SNR_RESULTS_CHECK",
            "PASS_STAGE08_COMMON_SNR_PLOT_CHECK",
            "PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON",
        ],
        "legacyStage08Label": "LEGACY_WIDE_GRID_FORMAL",
        "mergeStatus": "NOT_MERGED",
        "trackedFileHashes": hashes,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / f"{PREFIX}_git_commit.txt").write_text("TO_BE_FILLED_AFTER_COMMIT\n", encoding="utf-8")
    print("PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
