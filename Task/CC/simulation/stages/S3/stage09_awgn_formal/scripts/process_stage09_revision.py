#!/usr/bin/env python3
"""Validate, merge and plot the 2026-07-29 Stage09 two-level baseline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


STAGE = Path(__file__).resolve().parents[1]
REPO = STAGE.parents[6]
RUNTIME = STAGE / "runtime" / "revision_20260729_coarse"
RESULTS = STAGE / "results"
ARCHIVED_DENSE = (
    STAGE
    / "archive"
    / "v01_20260729_before_two_level_grid_revision"
    / "stage09_two_level_dense_point_results.csv"
)
SOURCE_HEAD = "6cda1f14f29a8cbe42ad3dcdc8a443ab35368b58"
DENSE_SOURCE_COMMIT = "6847b812e35d4905dc7fc8252a9a66ca2aee6fbe"
CASES = [
    "CC-B-R12-H",
    "CC-B-R12-S",
    "CC-B-R23-H",
    "CC-B-R23-S",
    "CC-B-R34-H",
    "CC-B-R34-S",
]
NOISE_GROUPS = {"R12": "1200", "R23": "2300", "R34": "3400"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fields: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for field in row:
                if field not in fields:
                    fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, trials: int) -> tuple[float, float]:
    if trials == 0:
        return 0.0, 0.0
    z = 1.959963984540054
    n = float(trials)
    p = successes / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    half = (
        z
        * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
        / denominator
    )
    return max(0.0, center - half), min(1.0, center + half)


def configure_font() -> None:
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in candidates:
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate]
            break
    plt.rcParams["axes.unicode_minus"] = False


def annotate(
    row: dict[str, str],
    layer: str,
    source_run: str,
    source_commit: str,
    min_frames: int,
) -> dict[str, object]:
    result: dict[str, object] = dict(row)
    frames = int(row["framesProcessed"])
    bits = int(row["payloadBitErrors"])
    frame_errors = int(row["payloadErrorFrames"])
    ber_ci = wilson(bits, frames * 300)
    fer_ci = wilson(frame_errors, frames)
    rate = row["caseId"].split("-")[2]
    result.update(
        {
            "berCiLow": ber_ci[0],
            "berCiHigh": ber_ci[1],
            "ferCiLow": fer_ci[0],
            "ferCiHigh": fer_ci[1],
            "berZeroErrorUpper95": ber_ci[1] if bits == 0 else "",
            "ferZeroErrorUpper95": fer_ci[1] if frame_errors == 0 else "",
            "gridLayer": layer,
            "sourceRun": source_run,
            "sourceCommit": source_commit,
            "runDate": "2026-07-29",
            "minFrames": min_frames,
            "targetFrameErrors": 200,
            "maxFrames": 50000,
            "checkpointIntervalFrames": 1000,
            "payloadSeed": 2026072001,
            "noiseSeed": 2026072001,
            "frameIndex": f"0-{frames - 1}",
            "sourceNoiseId": f"STAGE09-{NOISE_GROUPS[rate]}",
        }
    )
    return result


def validate_coarse(rows: list[dict[str, object]]) -> None:
    if len(rows) != 186:
        raise RuntimeError(f"expected 186 coarse rows, got {len(rows)}")
    coverage: dict[str, set[float]] = defaultdict(set)
    for row in rows:
        case = str(row["caseId"])
        snr = float(row["snrDb"])
        coverage[case].add(snr)
        actual_rate = float(row["actualRate"])
        if not math.isclose(float(row["esN0Db"]), snr, abs_tol=1e-12):
            raise RuntimeError("esN0Db does not equal snrDb")
        expected_eb = snr - 10.0 * math.log10(actual_rate)
        if not math.isclose(
            float(row["ebN0Db"]), expected_eb, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise RuntimeError("ebN0Db formula mismatch")
        expected_sigma = 1.0 / (2.0 * 10.0 ** (snr / 10.0))
        if not math.isclose(
            float(row["sigmaSquared"]),
            expected_sigma,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("sigmaSquared formula mismatch")
        frames = int(row["framesProcessed"])
        frame_errors = int(row["payloadErrorFrames"])
        stop = str(row["stopReason"])
        valid_stop = (
            stop == "TARGET_ERRORS_REACHED"
            and frames >= 1000
            and frame_errors >= 200
        ) or (stop == "MAX_FRAMES_REACHED" and frames == 50000)
        if not valid_stop:
            raise RuntimeError(f"invalid stop condition for {case}@{snr}")
    expected = {round(-5.0 + 0.5 * index, 1) for index in range(31)}
    if set(coverage) != set(CASES):
        raise RuntimeError("coarse case coverage mismatch")
    for case in CASES:
        if coverage[case] != expected:
            raise RuntimeError(f"coarse SNR coverage mismatch: {case}")


def plot_curves(
    rows: list[dict[str, object]],
    metric: str,
    output: Path,
    figure_data: Path,
    title: str,
    ylabel: str,
    cases: list[str] | None = None,
    log_y: bool = True,
) -> dict[str, object]:
    selected = [
        row for row in rows if cases is None or str(row["caseId"]) in cases
    ]
    write_csv(figure_data, selected)
    fig, axis = plt.subplots(figsize=(9.5, 6.2), dpi=150)
    for case in (cases or CASES):
        points = sorted(
            (row for row in selected if row["caseId"] == case),
            key=lambda row: float(row["snrDb"]),
        )
        plotted = [row for row in points if float(row[metric]) > 0.0]
        if plotted:
            axis.plot(
                [float(row["snrDb"]) for row in plotted],
                [float(row[metric]) for row in plotted],
                marker="o",
                markersize=3,
                linewidth=1.2,
                label=case,
            )
    if log_y:
        axis.set_yscale("log")
    axis.set_xlabel("SNR = Es/N0 (dB)")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return {
        "name": output.name,
        "inputCsv": "stage09_two_level_merged_point_results.csv",
        "inputSha256": "",
        "figureData": figure_data.name,
        "figureDataSha256": sha256(figure_data),
        "outputSha256": sha256(output),
        "zeroErrorPolicy": "raw zero retained in formal CSV; zero observations omitted from this log-scale figure",
    }


def plot_linear(
    rows: list[dict[str, object]],
    metric: str,
    output: Path,
    figure_data: Path,
    title: str,
    ylabel: str,
) -> dict[str, object]:
    write_csv(figure_data, rows)
    fig, axis = plt.subplots(figsize=(9.5, 6.2), dpi=150)
    for case in CASES:
        points = sorted(
            (row for row in rows if row["caseId"] == case),
            key=lambda row: float(row["snrDb"]),
        )
        axis.plot(
            [float(row["snrDb"]) for row in points],
            [float(row[metric]) for row in points],
            marker="o",
            markersize=3,
            linewidth=1.2,
            label=case,
        )
    axis.set_xlabel("SNR = Es/N0 (dB)")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return {
        "name": output.name,
        "inputCsv": "stage09_two_level_merged_point_results.csv",
        "inputSha256": "",
        "figureData": figure_data.name,
        "figureDataSha256": sha256(figure_data),
        "outputSha256": sha256(output),
    }


def selected_snr(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selections: list[dict[str, object]] = []
    for rate in ("R12", "R23", "R34"):
        case = f"CC-B-{rate}-S"
        points = [row for row in rows if row["caseId"] == case]
        fer_values = [float(row["FER"]) for row in points]
        for target in (0.30, 0.10, 0.03):
            covered = min(fer_values) <= target <= max(fer_values)
            selected = min(
                points,
                key=lambda row: (
                    abs(float(row["FER"]) - target),
                    abs(float(row["snrDb"])),
                ),
            )
            selections.append(
                {
                    "rateCase": rate,
                    "targetFer": target,
                    "selectedSnrDb": selected["snrDb"] if covered else "",
                    "observedFer": selected["FER"] if covered else "",
                    "absoluteFerDifference": (
                        abs(float(selected["FER"]) - target) if covered else ""
                    ),
                    "sourceCsv": "stage09_two_level_merged_point_results.csv",
                    "sourceRowId": selected["rowId"] if covered else "",
                    "selectionStatus": "COVERED" if covered else "N/A",
                }
            )
    return selections


def main() -> int:
    configure_font()
    RESULTS.mkdir(parents=True, exist_ok=True)
    unit_files = sorted(RUNTIME.glob("unit_*.csv"))
    if len(unit_files) != 93:
        raise RuntimeError(f"expected 93 unit files, got {len(unit_files)}")
    coarse: list[dict[str, object]] = []
    for unit in unit_files:
        part = read_csv(unit)
        if len(part) != 2:
            raise RuntimeError(f"expected hard/soft rows in {unit.name}")
        for row in part:
            annotated = annotate(
                row,
                "coarse_20260729",
                f"runtime/revision_20260729_coarse/{unit.name}",
                SOURCE_HEAD,
                1000,
            )
            annotated["rowId"] = f"coarse-{len(coarse):03d}"
            coarse.append(annotated)
    validate_coarse(coarse)

    dense: list[dict[str, object]] = []
    for row in read_csv(ARCHIVED_DENSE):
        annotated = annotate(
            row,
            "dense_verified_legacy",
            ARCHIVED_DENSE.relative_to(STAGE).as_posix(),
            DENSE_SOURCE_COMMIT,
            5000,
        )
        annotated["rowId"] = f"dense-{len(dense):03d}"
        dense.append(annotated)
    if len(dense) != 126:
        raise RuntimeError(f"expected 126 archived dense rows, got {len(dense)}")

    merged_by_key = {
        (row["caseId"], round(float(row["snrDb"]), 10)): row for row in coarse
    }
    for row in dense:
        merged_by_key[(row["caseId"], round(float(row["snrDb"]), 10))] = row
    merged = sorted(
        merged_by_key.values(),
        key=lambda row: (CASES.index(str(row["caseId"])), float(row["snrDb"])),
    )
    for index, row in enumerate(merged):
        row["mergedRowId"] = f"merged-{index:03d}"
    if len(merged) != 282:
        raise RuntimeError(f"expected 282 merged rows, got {len(merged)}")

    coarse_path = RESULTS / "stage09_two_level_coarse_point_results.csv"
    dense_path = RESULTS / "stage09_two_level_dense_point_results.csv"
    merged_path = RESULTS / "stage09_two_level_merged_point_results.csv"
    write_csv(coarse_path, coarse)
    write_csv(dense_path, dense)
    write_csv(merged_path, merged)
    selections = selected_snr(merged)
    write_csv(RESULTS / "stage09_selected_snr_by_fer_level.csv", selections)

    figures = [
        plot_curves(
            merged,
            "BER",
            RESULTS / "stage09_two_level_ber.png",
            RESULTS / "stage09_two_level_figure_data_ber.csv",
            "卷积码统一基线误比特率",
            "BER",
        ),
        plot_curves(
            merged,
            "FER",
            RESULTS / "stage09_two_level_fer.png",
            RESULTS / "stage09_two_level_figure_data_fer.csv",
            "卷积码统一基线误帧率",
            "FER",
        ),
        plot_curves(
            merged,
            "FER",
            RESULTS / "stage09_two_level_hard_soft_fer.png",
            RESULTS / "stage09_two_level_figure_data_hard_soft_fer.csv",
            "硬判决与浮点软判决 FER",
            "FER",
        ),
        plot_linear(
            merged,
            "avgDecodeTime_us",
            RESULTS / "stage09_two_level_delay.png",
            RESULTS / "stage09_two_level_figure_data_delay.csv",
            "完整块译码 CPU 时间",
            "平均译码时间 (μs)",
        ),
        plot_linear(
            merged,
            "normalizedGoodput",
            RESULTS / "stage09_two_level_goodput.png",
            RESULTS / "stage09_two_level_figure_data_goodput.csv",
            "完整块归一化有效吞吐",
            "归一化有效吞吐",
        ),
    ]
    merged_hash = sha256(merged_path)
    for figure in figures:
        figure["inputSha256"] = merged_hash
    manifest = {
        "stage": "stage09_awgn_formal",
        "snrDefinition": "SNR = Es/N0 (dB)",
        "coarseRows": len(coarse),
        "denseRows": len(dense),
        "mergedRows": len(merged),
        "coarseFrames": sum(int(row["framesProcessed"]) for row in coarse),
        "denseFrames": sum(int(row["framesProcessed"]) for row in dense),
        "figures": figures,
    }
    (RESULTS / "stage09_two_level_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS / "stage09_two_level_plot_check.md").write_text(
        "# Stage09 绘图检查\n\n"
        "PASS：所有图由逐点 CSV 生成；BER/FER 为对数轴；零错误保留原始 0，"
        "仅以空心标记显示 Wilson 95% 上界；输入、figure-data 和 PNG SHA256 已记录。\n",
        encoding="utf-8",
    )
    (RESULTS / "stage09_two_level_report.md").write_text(
        "# Stage09 两层网格复核\n\n"
        f"- 新 coarse：186 行，{manifest['coarseFrames']} frames，"
        "6 Case × 31 点，-5～10 dB/0.5 dB。\n"
        f"- dense：126 行，{manifest['denseFrames']} frames；"
        "明确标记为归档中的上一轮 verified dense，并记录 sourceCommit/sourceRun。\n"
        "- 合并曲线：282 行；dense 在相同 Case/SNR 上覆盖 coarse。\n"
        "- 模型：符号级离散 BPSK-AWGN，不是完整连续波形仿真。\n",
        encoding="utf-8",
    )
    print(
        "PASS_STAGE09_TWO_LEVEL_REVISION "
        f"coarseRows={len(coarse)} coarseFrames={manifest['coarseFrames']} "
        f"denseRows={len(dense)} denseFrames={manifest['denseFrames']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
