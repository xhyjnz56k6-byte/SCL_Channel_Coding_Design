from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DATA = (
    ROOT
    / "Task"
    / "CC"
    / "simulation"
    / "stages"
    / "S3"
    / "stage15_cc_s3_integration"
    / "results"
    / "figure_data"
)
OUTPUT = ROOT / "Report" / "figures" / "cc"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

RATE_LABEL = {"R12": "1/2母码", "R23": "约2/3打孔", "R34": "约3/4打孔"}
ORG_LABEL = {
    "A_BLOCK_300": "整块300",
    "B_CONT_50x6": "50×6",
    "C_CONT_100x3": "100×3",
    "D_CONT_150x2": "150×2",
}
COLORS = {"R12": "#1f77b4", "R23": "#d95f02", "R34": "#2ca02c"}
MARKERS = {"R12": "o", "R23": "s", "R34": "^"}


def rows(name: str) -> list[dict[str, str]]:
    with (FIGURE_DATA / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: str) -> float | None:
    return float(value) if value not in ("", None) else None


def setup() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font_manager.fontManager.addfont(str(FONT_PATH))
    plt.rcParams.update(
        {
            "font.family": "Microsoft YaHei",
            "font.size": 10.5,
            "axes.unicode_minus": False,
            "axes.grid": True,
            "grid.alpha": 0.24,
            "grid.linestyle": "--",
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUTPUT / name, facecolor="white")
    plt.close(fig)


def plot_block_soft_fer() -> None:
    data = rows("stage15_block_soft_fer_by_rate.csv")
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for rate in RATE_LABEL:
        points = sorted(
            (float(r["snrDb"]), float(r["FER"]))
            for r in data
            if r["rate"] == rate and float(r["FER"]) > 0.0
        )
        ax.semilogy(
            [p[0] for p in points],
            [p[1] for p in points],
            color=COLORS[rate],
            marker=MARKERS[rate],
            markevery=max(1, len(points) // 11),
            linewidth=1.8,
            markersize=4.2,
            label=RATE_LABEL[rate],
        )
    ax.set_xlabel(r"$E_s/N_0$ / dB")
    ax.set_ylabel("误帧率 FER")
    ax.set_title("不同码率浮点软判决的帧错误率")
    ax.set_ylim(1e-4, 1.2)
    ax.legend()
    fig.tight_layout()
    save(fig, "cc_rate_soft_fer_cn.png")


def plot_hard_soft_fer() -> None:
    data = rows("stage15_block_hard_soft_fer.csv")
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 3.9), sharey=True)
    for ax, rate in zip(axes, RATE_LABEL):
        for decision, label, style in (
            ("Hard", "硬判决", "--"),
            ("Soft Float", "浮点软判决", "-"),
        ):
            points = sorted(
                (float(r["snrDb"]), float(r["FER"]))
                for r in data
                if r["rate"] == rate
                and r["decisionMode"] == decision
                and float(r["FER"]) > 0.0
            )
            ax.semilogy(
                [p[0] for p in points],
                [p[1] for p in points],
                linestyle=style,
                linewidth=1.7,
                marker="o" if decision == "Soft Float" else "s",
                markevery=max(1, len(points) // 8),
                markersize=3.7,
                label=label,
            )
        ax.set_title(RATE_LABEL[rate])
        ax.set_xlabel(r"$E_s/N_0$ / dB")
        ax.set_ylim(1e-4, 1.2)
        ax.legend(fontsize=9)
    axes[0].set_ylabel("误帧率 FER")
    fig.suptitle("硬判决与浮点软判决的帧错误率比较", y=1.02)
    fig.tight_layout()
    save(fig, "cc_hard_soft_fer_cn.png")


def plot_traceback() -> None:
    data = rows("stage15_traceback_memory_reliability.csv")
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in data:
        grouped[int(float(row["dtb"]))].append(row)
    depths = sorted(grouped)
    median_fer = [np.median([float(r["relativeFerIncreaseVsBlock"]) for r in grouped[d]]) for d in depths]
    memory_kib = [float(grouped[d][0]["totalDecoderMemoryBytes"]) / 1024.0 for d in depths]
    first_output = [float(grouped[d][0]["firstDecisionDelaySymbols"]) for d in depths]

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.25))
    ax = axes[0]
    ax.plot(depths, median_fer, color="#b2182b", marker="o", linewidth=1.8)
    ax.axhline(0.05, color="#555555", linestyle="--", linewidth=1.2, label="5%判据")
    ax.set_xlabel("回溯深度 D")
    ax.set_ylabel("相对FER增幅（三码率中位数）")
    ax.set_title("可靠性变化")
    ax.legend()

    ax = axes[1]
    width = 5.0
    ax.bar(np.array(depths) - width / 2, memory_kib, width=width, color="#4c78a8", label="译码存储 / KiB")
    ax2 = ax.twinx()
    ax2.plot(depths, first_output, color="#f58518", marker="s", linewidth=1.8, label="首次输出 / 符号")
    ax.set_xlabel("回溯深度 D")
    ax.set_ylabel("译码存储 / KiB")
    ax2.set_ylabel("首次输出时延 / 符号")
    ax.set_title("存储与等待代价")
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, loc="upper left", fontsize=9)
    fig.suptitle("有限回溯深度的可靠性与资源权衡", y=1.02)
    fig.tight_layout()
    save(fig, "cc_traceback_tradeoff_cn.png")


def plot_quantization() -> None:
    data = rows("stage15_quantization_snr_loss.csv")
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for rate in RATE_LABEL:
        points = sorted(
            (int(r["quantMode"][1:]), float(r["snrLossVsFloat"]))
            for r in data
            if r["rateCase"] == rate
        )
        ax.plot(
            [p[0] for p in points],
            [p[1] for p in points],
            color=COLORS[rate],
            marker=MARKERS[rate],
            linewidth=1.8,
            label=RATE_LABEL[rate],
        )
    ax.axhline(0.0, color="#555555", linewidth=1.0)
    ax.set_xticks(range(3, 9), [f"Q{q}" for q in range(3, 9)])
    ax.set_xlabel("软信息量化位宽")
    ax.set_ylabel("FER=0.1时相对浮点的信噪比损失 / dB")
    ax.set_title("软信息量化位宽对译码性能的影响")
    ax.legend()
    fig.tight_layout()
    save(fig, "cc_quantization_loss_cn.png")


def plot_sliding_summary() -> None:
    data = rows("stage15_sliding_parameter_summary.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.9))
    configs = (
        ("CONTROL_W", "windowBits", "firstOutputDelaySymbols", "窗口长度 W", "首次输出时延 / 符号"),
        ("CONTROL_S", "slideBits", "p95DecisionDelaySymbols", "滑动步长 S", "第95百分位时延 / 符号"),
        ("CONTROL_D", "dtb", "relativeFerIncreaseVsBlock", "回溯深度 D", "相对整块FER增幅"),
    )
    for ax, (experiment, xkey, ykey, xlabel, ylabel) in zip(axes, configs):
        for rate in RATE_LABEL:
            points = sorted(
                (float(r[xkey]), float(r[ykey]))
                for r in data
                if r["experimentId"] == experiment and r["rateCase"] == rate
            )
            ax.plot(
                [p[0] for p in points],
                [p[1] for p in points],
                color=COLORS[rate],
                marker=MARKERS[rate],
                linewidth=1.7,
                label=RATE_LABEL[rate],
            )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8.5)
    fig.suptitle("滑窗参数控制变量结果汇总", y=1.02)
    fig.tight_layout()
    save(fig, "cc_sliding_parameter_summary_cn.png")


def plot_slot_latency() -> None:
    data = rows("stage15_slot_avg_p95_latency.csv")
    organizations = list(ORG_LABEL)
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.15), sharey=True)
    x = np.arange(len(organizations))
    width = 0.36
    for ax, rate in zip(axes, RATE_LABEL):
        rate_rows = {r["organization"]: r for r in data if r["rate"] == rate}
        first = [float(rate_rows[o]["firstOutputDelaySymbols"]) for o in organizations]
        p95 = [float(rate_rows[o]["p95DecisionDelaySymbols"]) for o in organizations]
        ax.bar(x - width / 2, first, width, label="首次输出", color="#4c78a8")
        ax.bar(x + width / 2, p95, width, label="第95百分位", color="#f58518")
        ax.set_xticks(x, [ORG_LABEL[o] for o in organizations], rotation=22, ha="right")
        ax.set_title(RATE_LABEL[rate])
        ax.set_xlabel("电文组织方式")
        ax.legend(fontsize=8.5)
    axes[0].set_ylabel("符号时延")
    fig.suptitle("不同时隙组织的浮点软判决输出时延", y=1.02)
    fig.tight_layout()
    save(fig, "cc_slot_latency_cn.png")


def main() -> None:
    setup()
    plot_block_soft_fer()
    plot_hard_soft_fer()
    plot_traceback()
    plot_quantization()
    plot_sliding_summary()
    plot_slot_latency()


if __name__ == "__main__":
    main()
