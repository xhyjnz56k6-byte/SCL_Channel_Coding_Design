from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[2]
S3 = ROOT / "Task" / "CC" / "simulation" / "stages" / "S3"
STAGE10 = S3 / "stage10_traceback_study" / "results"
STAGE11 = S3 / "stage11_soft_quantization" / "results"
STAGE13 = S3 / "stage13_sliding_window_viterbi" / "results"
STAGE14 = S3 / "stage14_block_continuous_comparison" / "results"
STAGE15 = S3 / "stage15_cc_s3_integration" / "results" / "figure_data"
OUTPUT = ROOT / "Report" / "figures" / "cc" / "round06_d"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

RATE_LABEL = {"R12": "1/2母码", "R23": "约2/3打孔", "R34": "约3/4打孔"}
ORG_LABEL = {
    "A_BLOCK_300": "整块300",
    "B_CONT_50x6": "50×6",
    "C_CONT_100x3": "100×3",
    "D_CONT_150x2": "150×2",
}
COLORS = ["#1f77b4", "#d95f02", "#2ca02c", "#9467bd", "#8c564b", "#17becf", "#222222"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def positive_points(data: list[dict[str, str]], metric: str) -> list[dict[str, str]]:
    return sorted((row for row in data if float(row[metric]) > 0.0), key=lambda row: float(row["snrDb"]))


def plot_three_rate_curves(
    data: list[dict[str, str]], group_key: str, groups: list[str], labels: dict[str, str],
    metric: str, title: str, filename: str,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.0), sharey=True)
    for ax, rate in zip(axes, RATE_LABEL):
        rate_rows = [row for row in data if row["rateCase"] == rate]
        for index, group in enumerate(groups):
            points = positive_points([row for row in rate_rows if row[group_key] == group], metric)
            if not points:
                continue
            ax.semilogy(
                [float(row["snrDb"]) for row in points], [float(row[metric]) for row in points],
                color=COLORS[index], marker=MARKERS[index], markersize=3.1, linewidth=1.25,
                markevery=max(1, len(points) // 9), label=labels[group],
            )
        ax.set_title(RATE_LABEL[rate])
        ax.set_xlabel(r"$E_s/N_0$ / dB")
        ax.set_ylim(1e-4, 1.2)
        ax.legend(fontsize=7.7, ncol=2)
    axes[0].set_ylabel("比特错误率 BER" if metric == "BER" else "帧错误率 FER")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    save(fig, filename)


def plot_traceback_fer() -> None:
    # The published FER figure_data contains only finite-depth rows; the official
    # result table additionally supplies the full-traceback baseline.
    data = read_csv(STAGE10 / "stage10_traceback_study_results.csv")
    depths = ["35", "49", "70", "84", "98", "112", "306"]
    labels = {value: ("完整回溯" if value == "306" else f"D={value}") for value in depths}
    plot_three_rate_curves(data, "dtb", depths, labels, "FER", "不同回溯深度下的卷积码帧错误率", "cc_traceback_fer_cn.png")


def plot_traceback_cpu() -> None:
    data = read_csv(STAGE10 / "stage10_traceback_cpu_latency_figure_data.csv")
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in data:
        grouped[int(row["dtb"])].append(float(row["avgDecodeTimeUs"]))
    depths = sorted(grouped)
    values = [np.mean(grouped[depth]) for depth in depths]
    labels = ["完整" if depth == 306 else str(depth) for depth in depths]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.bar(labels, values, color="#4c78a8")
    ax.set_xlabel("回溯深度 D")
    ax.set_ylabel("平均软件译码时间 / μs·帧$^{-1}$")
    ax.set_title("不同回溯深度下的软件译码时间")
    ax.text(0.99, 0.03, "本机处理器、当前编译器与串行实现", transform=ax.transAxes, ha="right", fontsize=9)
    fig.tight_layout()
    save(fig, "cc_traceback_cpu_cn.png")


def plot_traceback_tradeoff() -> None:
    data = read_csv(STAGE15 / "stage15_traceback_memory_reliability.csv")
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in data:
        grouped[int(float(row["dtb"]))].append(row)
    depths = sorted(grouped)
    worst = [max(float(row["relativeFerIncreaseVsBlock"]) for row in grouped[depth]) for depth in depths]
    median = [float(np.median([float(row["relativeFerIncreaseVsBlock"]) for row in grouped[depth]])) for depth in depths]
    memory = [float(grouped[depth][0]["totalDecoderMemoryBytes"]) / 1024 for depth in depths]
    first = [float(grouped[depth][0]["firstDecisionDelaySymbols"]) for depth in depths]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.25))
    axes[0].plot(depths, worst, color="#b2182b", marker="o", label="全工作点最坏值")
    axes[0].plot(depths, median, color="#666666", marker="s", linestyle=":", label="三码率中位数")
    axes[0].axhline(0.05, color="#222222", linestyle="--", linewidth=1.2, label="5%判据")
    axes[0].set(xlabel="回溯深度 D", ylabel="相对完整回溯的 FER 增幅", title="可靠性判据")
    axes[0].legend(fontsize=8.5)
    x = np.arange(len(depths))
    axes[1].bar(x, memory, color="#4c78a8", label="译码存储 / KiB")
    ax2 = axes[1].twinx()
    ax2.plot(x, first, color="#f58518", marker="s", label="首次输出 / 符号")
    axes[1].set_xticks(x, depths)
    axes[1].set(xlabel="回溯深度 D", ylabel="译码存储 / KiB", title="存储与等待代价")
    ax2.set_ylabel("首次输出时延 / 符号")
    h1, l1 = axes[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    axes[1].legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left")
    fig.suptitle("有限回溯深度的可靠性与资源权衡", y=1.02)
    fig.tight_layout()
    save(fig, "cc_traceback_tradeoff_cn.png")


def plot_quantization_fer() -> None:
    modes = ["Float", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
    labels = {"Float": "浮点", **{f"Q{bits}": f"{bits} bit" for bits in range(3, 9)}}
    data: list[dict[str, str]] = []
    for rate in RATE_LABEL:
        data.extend(read_csv(STAGE11 / f"stage11_{rate.lower()}_quantization_fer_figure_data.csv"))
    plot_three_rate_curves(data, "quantMode", modes, labels, "FER", "不同软信息量化位宽下的卷积码帧错误率", "cc_quantization_fer_cn.png")


def plot_quantization_loss() -> None:
    data = read_csv(STAGE15 / "stage15_quantization_snr_loss.csv")
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for index, rate in enumerate(RATE_LABEL):
        points = sorted((int(row["quantMode"][1:]), float(row["snrLossVsFloat"])) for row in data if row["rateCase"] == rate)
        ax.plot([p[0] for p in points], [p[1] for p in points], color=COLORS[index], marker=MARKERS[index], label=RATE_LABEL[rate])
    ax.axhline(0, color="#555555", linewidth=1)
    ax.set_xticks(range(3, 9), [f"{bits} bit" for bits in range(3, 9)])
    ax.set(xlabel="软信息量化位宽", ylabel="FER=0.1 时相对浮点的信噪比损失 / dB", title="量化位宽对译码性能的影响")
    ax.legend()
    fig.tight_layout()
    save(fig, "cc_quantization_loss_cn.png")


def plot_sliding_control(experiment: str, parameter: str, values: list[int], fixed: str, filename: str) -> None:
    suffix = {"windowBits": "windowbits", "slideBits": "slidebits", "dtb": "dtb"}[parameter]
    data: list[dict[str, str]] = []
    for rate in RATE_LABEL:
        data.extend(read_csv(STAGE13 / "figure_data" / f"stage13_{rate.lower()}_{suffix}_fer_snr.csv"))
    labels = {str(value): f"{parameter[0].upper()}={value}" for value in values}
    for row in data:
        row[parameter] = str(int(float(row[parameter])))
    title_name = {"windowBits": "窗口长度 W", "slideBits": "滑动步长 S", "dtb": "回溯深度 D"}[parameter]
    plot_three_rate_curves(data, parameter, [str(v) for v in values], labels, "FER", f"不同{title_name}对滑窗译码 FER 的影响（固定{fixed}）", filename)


def plot_slot_reliability(decision: str, metric: str, filename: str) -> None:
    token = "hard" if decision == "Hard" else "soft"
    data: list[dict[str, str]] = []
    for rate in RATE_LABEL:
        data.extend(read_csv(STAGE14 / "figure_data" / f"stage14_{rate.lower()}_{token}_{metric.lower()}_by_organization.csv"))
    plot_three_rate_curves(data, "organization", list(ORG_LABEL), ORG_LABEL, metric,
                           f"不同电文组织的{'硬判决' if decision == 'Hard' else '浮点软判决'} {metric}", filename)


def plot_slot_latency() -> None:
    data = read_csv(STAGE14 / "figure_data" / "stage14_soft_avg_p95_decision_latency.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.15), sharey=True)
    x = np.arange(len(ORG_LABEL)); width = 0.36
    for ax, rate in zip(axes, RATE_LABEL):
        lookup = {row["organization"]: row for row in data if row["rateCase"] == rate}
        ax.bar(x - width / 2, [float(lookup[o]["firstOutputDelaySymbols"]) for o in ORG_LABEL], width, label="首次输出", color="#4c78a8")
        ax.bar(x + width / 2, [float(lookup[o]["p95DecisionDelaySymbols"]) for o in ORG_LABEL], width, label="第95百分位", color="#f58518")
        ax.set_xticks(x, [ORG_LABEL[o] for o in ORG_LABEL], rotation=20, ha="right")
        ax.set_title(RATE_LABEL[rate]); ax.set_xlabel("电文组织方式"); ax.legend(fontsize=8)
    axes[0].set_ylabel("符号时延")
    fig.suptitle("不同电文组织的浮点软判决输出时延", y=1.02)
    fig.tight_layout(); save(fig, "cc_slot_latency_cn.png")


def plot_soft_goodput() -> None:
    data = read_csv(STAGE15 / "stage15_slot_soft_goodput.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.0), sharey=True)
    for ax, rate in zip(axes, RATE_LABEL):
        for index, organization in enumerate(ORG_LABEL):
            points = sorted(
                (row for row in data if row["rate"] == rate and row["organization"] == organization),
                key=lambda row: float(row["snrDb"]),
            )
            ax.plot(
                [float(row["snrDb"]) for row in points],
                [float(row["normalizedGoodput"]) for row in points],
                color=COLORS[index], marker=MARKERS[index], markersize=3.1,
                linewidth=1.25, markevery=max(1, len(points) // 9), label=ORG_LABEL[organization],
            )
        ax.set_title(RATE_LABEL[rate]); ax.set_xlabel(r"$E_s/N_0$ / dB")
        ax.set_ylim(-0.02, 0.78); ax.legend(fontsize=7.7)
    axes[0].set_ylabel("归一化有效吞吐率")
    fig.suptitle("不同电文组织的浮点软判决归一化有效吞吐率", y=1.02)
    fig.tight_layout(); save(fig, "cc_slot_soft_goodput_cn.png")


def main() -> None:
    setup()
    plot_traceback_fer(); plot_traceback_cpu(); plot_traceback_tradeoff()
    plot_quantization_fer(); plot_quantization_loss()
    plot_sliding_control("CONTROL_W", "windowBits", [96, 128, 160, 192], "S=16，D=70", "cc_sliding_w_fer_cn.png")
    plot_sliding_control("CONTROL_S", "slideBits", [8, 16, 25, 50], "W=160，D=70", "cc_sliding_s_fer_cn.png")
    plot_sliding_control("CONTROL_D", "dtb", [35, 49, 70, 84, 98, 112], "W=160，S=16", "cc_sliding_d_fer_cn.png")
    plot_slot_reliability("Hard", "BER", "cc_slot_hard_ber_cn.png")
    plot_slot_reliability("Hard", "FER", "cc_slot_hard_fer_cn.png")
    plot_slot_reliability("Soft Float", "BER", "cc_slot_soft_ber_cn.png")
    plot_slot_reliability("Soft Float", "FER", "cc_slot_soft_fer_cn.png")
    plot_slot_latency(); plot_soft_goodput()


if __name__ == "__main__":
    main()
