#!/usr/bin/env python3
"""Validate and publish the three-rate/three-FER-level traceback study."""

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
RESULTS = STAGE / "results"
SOURCE = RESULTS / "stage10_traceback_study_results.csv"
DEPTHS = [35, 49, 70, 84, 98, 112]
RATES = ["R12", "R23", "R34"]
LEVELS = ["FER_030", "FER_010", "FER_003"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def validate(rows: list[dict[str, str]]) -> None:
    if len(rows) != 63:
        raise RuntimeError(f"expected 63 result rows, got {len(rows)}")
    expected = {
        (rate, level, mode, depth)
        for rate in RATES
        for level in LEVELS
        for mode, depth in [
            ("BLOCK_FULL_TRACEBACK", 306),
            *[("CONTINUOUS_TRUNCATED_VITERBI", value) for value in DEPTHS],
        ]
    }
    observed = {
        (row["rateCase"], row["targetFerLevel"], row["mode"], int(row["dtb"]))
        for row in rows
    }
    if observed != expected:
        raise RuntimeError("traceback coverage matrix mismatch")
    for row in rows:
        snr = float(row["snrDb"])
        rate = float(row["actualRate"])
        if not math.isclose(float(row["esN0Db"]), snr, abs_tol=1e-12):
            raise RuntimeError("Es/N0 field mismatch")
        if not math.isclose(
            float(row["ebN0Db"]),
            snr - 10.0 * math.log10(rate),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("Eb/N0 field mismatch")
        if not math.isclose(
            float(row["sigmaSquared"]),
            1.0 / (2.0 * 10.0 ** (snr / 10.0)),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("noise variance mismatch")
        frames = int(row["frames"])
        frame_errors = int(row["frameErrors"])
        stop = row["stopReason"]
        if not (
            (
                stop == "TARGET_ERRORS_REACHED"
                and frames >= 1000
                and frame_errors >= 200
            )
            or (stop == "MAX_FRAMES_REACHED" and frames == 50000)
        ):
            raise RuntimeError("formal stopping condition mismatch")


def finite(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row["mode"] == "CONTINUOUS_TRUNCATED_VITERBI"
    ]


def plot_metric(
    rows: list[dict[str, str]],
    metric: str,
    filename: str,
    title: str,
    ylabel: str,
    log_y: bool = False,
) -> dict[str, str]:
    data = finite(rows)
    data_path = RESULTS / filename.replace(".png", "_figure_data.csv")
    write_csv(data_path, data)
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=150)
    for axis, rate in zip(axes, RATES):
        for level in LEVELS:
            points = sorted(
                (
                    row
                    for row in data
                    if row["rateCase"] == rate
                    and row["targetFerLevel"] == level
                ),
                key=lambda row: int(row["dtb"]),
            )
            axis.plot(
                [int(row["dtb"]) for row in points],
                [float(row[metric]) for row in points],
                marker="o",
                label=level.replace("FER_", "目标FER "),
            )
        axis.set_title(rate)
        axis.set_xlabel("回溯深度 Dtb (bit)")
        axis.grid(True, which="both", alpha=0.25)
        if log_y:
            axis.set_yscale("log")
    axes[0].set_ylabel(ylabel)
    axes[-1].legend(fontsize=8)
    figure.suptitle(title)
    figure.tight_layout()
    output = RESULTS / filename
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": filename,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def plot_memory(rows: list[dict[str, str]]) -> dict[str, str]:
    unique: dict[int, dict[str, str]] = {}
    for row in finite(rows):
        unique[int(row["dtb"])] = row
    data = [unique[depth] for depth in DEPTHS]
    data_path = RESULTS / "stage10_traceback_memory_figure_data.csv"
    write_csv(data_path, data)
    figure, axis = plt.subplots(figsize=(8, 5.5), dpi=150)
    axis.plot(
        DEPTHS,
        [float(row["survivorMemoryBytes"]) / 1024.0 for row in data],
        marker="o",
    )
    axis.set(
        title="回溯深度与幸存路径内存",
        xlabel="回溯深度 Dtb (bit)",
        ylabel="幸存路径内存 (KiB)",
    )
    axis.grid(True, alpha=0.25)
    figure.tight_layout()
    output = RESULTS / "stage10_traceback_memory.png"
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": output.name,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def plot_tradeoff(rows: list[dict[str, str]]) -> dict[str, str]:
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in finite(rows):
        grouped[int(row["dtb"])].append(row)
    data = [
        {
            "dtb": depth,
            "totalDecoderMemoryBytes": grouped[depth][0][
                "totalDecoderMemoryBytes"
            ],
            "worstRelativeFerIncrease": max(
                float(row["relativeFerIncreaseVsBlock"])
                for row in grouped[depth]
            ),
            "worstRelativeBerIncrease": max(
                float(row["relativeBerIncreaseVsBlock"])
                for row in grouped[depth]
            ),
        }
        for depth in DEPTHS
    ]
    data_path = RESULTS / "stage10_memory_reliability_tradeoff_figure_data.csv"
    write_csv(data_path, data)
    figure, axis = plt.subplots(figsize=(8, 5.5), dpi=150)
    for row in data:
        x = float(row["totalDecoderMemoryBytes"]) / 1024.0
        y = float(row["worstRelativeFerIncrease"]) * 100.0
        axis.scatter(x, y, s=55)
        axis.annotate(f"D{row['dtb']}", (x, y), xytext=(4, 4), textcoords="offset points")
    axis.axhline(5.0, color="tab:red", linestyle="--", label="可靠性门限 5%")
    axis.set(
        title="回溯深度内存—可靠性权衡",
        xlabel="总译码内存 (KiB)",
        ylabel="最坏相对 FER 增幅 (%)",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    output = RESULTS / "stage10_memory_reliability_tradeoff.png"
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": output.name,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def recommendations(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in finite(rows):
        grouped[int(row["dtb"])].append(row)
    summary = []
    for depth in DEPTHS:
        points = grouped[depth]
        summary.append(
            {
                "dtb": depth,
                "worstRelativeFerIncrease": max(
                    float(row["relativeFerIncreaseVsBlock"]) for row in points
                ),
                "worstRelativeBerIncrease": max(
                    float(row["relativeBerIncreaseVsBlock"]) for row in points
                ),
                "totalDecoderMemoryBytes": int(
                    points[0]["totalDecoderMemoryBytes"]
                ),
                "meanDecodeTimeUs": sum(
                    float(row["avgDecodeTimeUs"]) for row in points
                )
                / len(points),
                "meanFirstDecisionDelaySymbols": sum(
                    float(row["firstDecisionDelaySymbols"]) for row in points
                )
                / len(points),
            }
        )
    qualified = [
        row for row in summary if row["worstRelativeFerIncrease"] <= 0.05
    ]
    performance = min(
        qualified, key=lambda row: row["worstRelativeFerIncrease"]
    )
    balanced = min(
        qualified,
        key=lambda row: (
            0.5 * row["worstRelativeFerIncrease"] / 0.05
            + 0.25 * row["totalDecoderMemoryBytes"]
            / max(item["totalDecoderMemoryBytes"] for item in qualified)
            + 0.25 * row["meanDecodeTimeUs"]
            / max(item["meanDecodeTimeUs"] for item in qualified)
        ),
    )
    memory = min(qualified, key=lambda row: row["totalDecoderMemoryBytes"])
    latency = min(
        qualified, key=lambda row: row["meanFirstDecisionDelaySymbols"]
    )
    chosen = {
        "performanceFirstRecommendation": performance["dtb"],
        "balancedRecommendation": balanced["dtb"],
        "memoryFirstRecommendation": memory["dtb"],
        "latencyFirstRecommendation": latency["dtb"],
    }
    for row in summary:
        row.update(chosen)
        row["reliabilityGate"] = (
            "PASS"
            if row["worstRelativeFerIncrease"] <= 0.05
            else "FAIL"
        )
    return summary


def main() -> int:
    font()
    rows = read_csv(SOURCE)
    validate(rows)
    recommendation_rows = recommendations(rows)
    write_csv(
        RESULTS / "stage10_traceback_recommendation.csv",
        recommendation_rows,
    )
    figures = [
        plot_metric(
            rows,
            "BER",
            "stage10_traceback_ber.png",
            "回溯深度与误比特率",
            "BER",
            True,
        ),
        plot_metric(
            rows,
            "FER",
            "stage10_traceback_fer.png",
            "回溯深度与误帧率",
            "FER",
            True,
        ),
        plot_metric(
            rows,
            "avgDecodeTimeUs",
            "stage10_traceback_cpu_latency.png",
            "回溯深度与 CPU 译码时间",
            "平均译码时间 (μs)",
        ),
        plot_memory(rows),
        plot_metric(
            rows,
            "relativeFerIncreaseVsBlock",
            "stage10_traceback_relative_fer_loss.png",
            "回溯深度相对完整块 FER 增幅",
            "相对 FER 增幅",
        ),
        plot_tradeoff(rows),
    ]
    manifest = {
        "stage": "stage10_traceback_study",
        "inputCsv": SOURCE.name,
        "inputSha256": sha(SOURCE),
        "blockReferencePolicy": (
            "完整块与有限回溯采用不同调度；完整块不与有限深度折线连接"
        ),
        "figures": figures,
    }
    (RESULTS / "stage10_traceback_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    selected = int(
        recommendation_rows[0]["balancedRecommendation"]
    )
    (RESULTS / "stage10_traceback_plot_check.md").write_text(
        "# Stage10 绘图检查\n\nPASS：6 张图均从正式 CSV 逐点生成；"
        "完整块未与有限回溯 CPU 折线连接；输入与输出 SHA256 已记录。\n",
        encoding="utf-8",
    )
    (RESULTS / "stage10_traceback_report.md").write_text(
        "# Stage10 正式回溯深度研究\n\n"
        "- 覆盖 R12/R23/R34、FER≈0.30/0.10/0.03、Dtb=35/49/70/84/98/112 与完整块。\n"
        f"- 5% 最坏相对 FER 增幅 Gate 下，当前 balanced Dtb={selected}。\n"
        "- D84 真滑窗联合复核尚待 Stage13 正式结果；在此之前该结论仅为连续有限回溯推荐。\n",
        encoding="utf-8",
    )
    print(f"PASS_STAGE10_REVISION balancedDtb={selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
