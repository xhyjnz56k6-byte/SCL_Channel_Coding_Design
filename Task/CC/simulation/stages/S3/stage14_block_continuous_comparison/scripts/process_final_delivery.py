#!/usr/bin/env python3
"""Merge Stage14 Hard/Soft formal data and build final core figures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
FIGURE_DATA = RESULTS / "figure_data"
SOFT_ARCHIVE = (
    STAGE
    / "archive"
    / "v03_20260731_before_hard_slot_completion"
)
HARD_RUNTIME = STAGE / "runtime" / "final_delivery_hard"
RATES = ["R12", "R23", "R34"]
ORGANIZATIONS = [
    "A_BLOCK_300",
    "B_CONT_50x6",
    "C_CONT_100x3",
    "D_CONT_150x2",
]
LABELS = {
    "A_BLOCK_300": "Block300",
    "B_CONT_50x6": "50x6",
    "C_CONT_100x3": "100x3",
    "D_CONT_150x2": "150x2",
}
STYLES = {
    "A_BLOCK_300": ("#1f77b4", "-", "o"),
    "B_CONT_50x6": ("#d62728", "--", "s"),
    "C_CONT_100x3": ("#2ca02c", "-.", "^"),
    "D_CONT_150x2": ("#9467bd", ":", "D"),
}


def configure_font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_recommendations() -> dict[str, tuple[int, int, int]]:
    path = (
        STAGE.parent
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_final_recommendations.csv"
    )
    data = pd.read_csv(path)
    data = data[data.recommendationType == "balanced"]
    return {
        row.rateCase: (
            int(row.windowBits),
            int(row.slideBits),
            int(row.dtb),
        )
        for _, row in data.iterrows()
    }


def add_configuration(
    data: pd.DataFrame,
    decision: str,
    configs: dict[str, tuple[int, int, int]],
) -> pd.DataFrame:
    data = data.copy()
    data["decisionMode"] = decision
    for column in ("windowBits", "slideBits", "dtb"):
        if column not in data:
            data[column] = 0
    for index, row in data.iterrows():
        if row.organization == "A_BLOCK_300":
            values = (306, 300, 306)
        else:
            values = configs[row.rateCase]
        data.loc[index, ["windowBits", "slideBits", "dtb"]] = values
    data["stopReason"] = data.stopReason.replace(
        {"TARGET_ERRORS_REACHED": "TARGET_FRAME_ERRORS_REACHED"}
    )
    return data


def load_formal() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    configs = load_recommendations()
    soft = add_configuration(
        pd.read_csv(
            SOFT_ARCHIVE / "stage14_online_slot_formal_results.csv"
        ),
        "Soft Float",
        configs,
    )
    hard_paths = sorted(
        path
        for path in HARD_RUNTIME.glob("unit_*.csv")
        if not path.name.endswith("_offsets.csv")
    )
    if len(hard_paths) != 93:
        raise RuntimeError(f"Hard runtime incomplete: {len(hard_paths)}/93")
    hard = add_configuration(
        pd.concat((pd.read_csv(path) for path in hard_paths), ignore_index=True),
        "Hard",
        configs,
    )
    offsets_soft = pd.read_csv(
        SOFT_ARCHIVE / "stage14_boundary_offset_results.csv"
    )
    offset_paths = sorted(HARD_RUNTIME.glob("unit_*_offsets.csv"))
    offsets_hard = pd.concat(
        (pd.read_csv(path) for path in offset_paths), ignore_index=True
    )
    offsets_soft["decisionMode"] = "Soft Float"
    offsets_hard["decisionMode"] = "Hard"
    offsets = pd.concat([offsets_soft, offsets_hard], ignore_index=True)
    all_data = pd.concat([soft, hard], ignore_index=True)
    columns = [
        "organization",
        "rateCase",
        "decisionMode",
        "windowBits",
        "slideBits",
        "dtb",
    ]
    columns += [name for name in all_data.columns if name not in columns]
    all_data = all_data[columns].sort_values(
        ["decisionMode", "rateCase", "organization", "snrDb"]
    )
    return soft, hard, all_data, offsets


def validate(data: pd.DataFrame) -> None:
    if len(data) != 744:
        raise RuntimeError(f"expected 744 rows, got {len(data)}")
    expected_snr = np.round(np.arange(-5.0, 10.01, 0.5), 10)
    for decision in ("Hard", "Soft Float"):
        part = data[data.decisionMode == decision]
        if len(part) != 372:
            raise RuntimeError(f"{decision} row count is {len(part)}")
        for rate in RATES:
            for organization in ORGANIZATIONS:
                case = part[
                    (part.rateCase == rate)
                    & (part.organization == organization)
                ]
                if len(case) != 31 or not np.allclose(
                    sorted(case.snrDb), expected_snr
                ):
                    raise RuntimeError(
                        f"incomplete case {decision}/{rate}/{organization}"
                    )
    if not (data.frames >= 1000).all():
        raise RuntimeError("a formal point has fewer than 1000 frames")
    target = data.stopReason == "TARGET_FRAME_ERRORS_REACHED"
    maximum = data.stopReason == "MAX_FRAMES_REACHED"
    if not (
        (target & (data.frameErrors >= 200))
        | (maximum & (data.frames == 50000))
    ).all():
        raise RuntimeError("invalid formal stopping condition")
    if not np.allclose(data.BER, data.bitErrors / (data.frames * 300)):
        raise RuntimeError("BER arithmetic mismatch")
    if not np.allclose(data.FER, data.frameErrors / data.frames):
        raise RuntimeError("FER arithmetic mismatch")
    if not np.allclose(
        data.normalizedGoodput, data.actualRate * (1.0 - data.FER)
    ):
        raise RuntimeError("goodput arithmetic mismatch")


def figure_csv(name: str, data: pd.DataFrame) -> Path:
    path = FIGURE_DATA / f"{name}.csv"
    data.to_csv(path, index=False)
    if path.stat().st_size == 0 or data.empty:
        raise RuntimeError(f"empty figure data: {name}")
    return path


def save(
    name: str,
    data: pd.DataFrame,
    manifest: list[dict],
) -> None:
    source = figure_csv(name, data)
    path = RESULTS / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    manifest.append(
        {
            "plot": path.name,
            "figureData": source.relative_to(RESULTS).as_posix(),
            "rows": len(data),
            "plotSha256": sha256(path),
            "figureDataSha256": sha256(source),
        }
    )


def plot_error_curves(
    data: pd.DataFrame, manifest: list[dict]
) -> None:
    for decision, token in (("Soft Float", "soft"), ("Hard", "hard")):
        for rate in RATES:
            part = data[
                (data.decisionMode == decision) & (data.rateCase == rate)
            ]
            for metric in ("BER", "FER"):
                name = (
                    f"stage14_{rate.lower()}_{token}_"
                    f"{metric.lower()}_by_organization"
                )
                plt.figure(figsize=(7.6, 5.0))
                for organization in ORGANIZATIONS:
                    group = part[
                        part.organization == organization
                    ].sort_values("snrDb")
                    color, line, marker = STYLES[organization]
                    values = group[metric].clip(lower=1e-8)
                    plt.semilogy(
                        group.snrDb,
                        values,
                        color=color,
                        linestyle=line,
                        marker=marker,
                        markersize=3,
                        linewidth=1.2,
                        label=LABELS[organization],
                    )
                plt.xlabel("SNR = Es/N0 (dB)")
                plt.ylabel(metric)
                plt.title(f"{rate} {decision}: {metric}")
                plt.grid(True, which="both", alpha=0.25)
                plt.legend()
                save(name, part, manifest)


def plot_goodput(data: pd.DataFrame, manifest: list[dict]) -> None:
    for decision, token in (("Soft Float", "soft"), ("Hard", "hard")):
        part = data[data.decisionMode == decision]
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
        for axis, rate in zip(axes, RATES):
            for organization in ORGANIZATIONS:
                group = part[
                    (part.rateCase == rate)
                    & (part.organization == organization)
                ].sort_values("snrDb")
                color, line, marker = STYLES[organization]
                axis.plot(
                    group.snrDb,
                    group.normalizedGoodput,
                    color=color,
                    linestyle=line,
                    marker=marker,
                    markersize=2.5,
                    label=LABELS[organization],
                )
            axis.set_title(rate)
            axis.set_xlabel("SNR = Es/N0 (dB)")
            axis.grid(True, alpha=0.25)
        axes[0].set_ylabel("Normalized goodput")
        axes[-1].legend(fontsize=8)
        fig.suptitle(f"{decision}: rate and organization goodput")
        save(
            f"stage14_{token}_goodput_by_rate_and_organization",
            part,
            manifest,
        )


def representative(data: pd.DataFrame, decision: str) -> pd.DataFrame:
    columns = [
        "firstOutputDelaySymbols",
        "avgDecisionDelaySymbols",
        "p95DecisionDelaySymbols",
        "peakRxBufferSymbols",
        "totalMemoryBytes",
        "ACSCount",
        "tracebackOperations",
        "outputBatchCount",
        "fullFrameLastDecisionSymbol",
    ]
    return (
        data[data.decisionMode == decision]
        .groupby(["rateCase", "organization"], as_index=False)[columns]
        .median()
    )


def plot_latency_and_compute(
    data: pd.DataFrame, manifest: list[dict]
) -> None:
    x = np.arange(len(ORGANIZATIONS))
    for decision, token in (("Soft Float", "soft"), ("Hard", "hard")):
        summary = representative(data, decision)
        plt.figure(figsize=(8, 4.8))
        for rate in RATES:
            group = summary.set_index(
                ["rateCase", "organization"]
            ).loc[rate].reindex(ORGANIZATIONS)
            plt.plot(
                x,
                group.firstOutputDelaySymbols,
                marker="o",
                label=rate,
            )
        plt.xticks(x, [LABELS[item] for item in ORGANIZATIONS])
        plt.ylabel("First output delay (symbols)")
        plt.title(f"{decision}: first output latency")
        plt.grid(True, alpha=0.25)
        plt.legend()
        save(f"stage14_{token}_first_output_latency", summary, manifest)

        fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
        for axis, rate in zip(axes, RATES):
            group = summary.set_index(
                ["rateCase", "organization"]
            ).loc[rate].reindex(ORGANIZATIONS)
            axis.bar(x - 0.18, group.avgDecisionDelaySymbols, 0.36, label="Avg")
            axis.bar(x + 0.18, group.p95DecisionDelaySymbols, 0.36, label="P95")
            axis.set_xticks(x, [LABELS[item] for item in ORGANIZATIONS])
            axis.set_title(rate)
            axis.grid(True, axis="y", alpha=0.25)
        axes[0].set_ylabel("Decision delay (symbols)")
        axes[-1].legend()
        fig.suptitle(f"{decision}: average and P95 decision latency")
        save(
            f"stage14_{token}_avg_p95_decision_latency",
            summary,
            manifest,
        )

        fig, axes = plt.subplots(2, 2, figsize=(11, 8))
        metrics = [
            ("peakRxBufferSymbols", "Peak RX buffer (symbols)"),
            ("totalMemoryBytes", "Total decoder memory (bytes)"),
            ("ACSCount", "ACS count"),
            ("tracebackOperations", "Traceback operations"),
        ]
        for axis, (metric, ylabel) in zip(axes.flat, metrics):
            for rate in RATES:
                group = summary.set_index(
                    ["rateCase", "organization"]
                ).loc[rate].reindex(ORGANIZATIONS)
                axis.plot(x, group[metric], marker="o", label=rate)
            axis.set_xticks(x, [LABELS[item] for item in ORGANIZATIONS])
            axis.set_ylabel(ylabel)
            axis.grid(True, alpha=0.25)
        axes[0, 0].legend()
        fig.suptitle(f"{decision}: buffering and computation")
        save(
            f"stage14_{token}_buffer_compute_tradeoff",
            summary,
            manifest,
        )


def plot_progress(data: pd.DataFrame, manifest: list[dict]) -> None:
    soft = representative(data, "Soft Float")
    for rate in RATES:
        rows = []
        plt.figure(figsize=(7.6, 4.8))
        for organization in ORGANIZATIONS[1:]:
            point = soft[
                (soft.rateCase == rate)
                & (soft.organization == organization)
            ].iloc[0]
            batches = max(2, int(round(point.outputBatchCount)))
            received = np.linspace(
                point.firstOutputDelaySymbols,
                point.fullFrameLastDecisionSymbol,
                batches,
            )
            decoded = np.linspace(300 / batches, 300, batches)
            plt.step(
                received,
                decoded,
                where="post",
                label=LABELS[organization],
            )
            rows.extend(
                {
                    "rateCase": rate,
                    "organization": organization,
                    "receivedSymbolIndex": symbol_index,
                    "cumulativeDecodedPayloadBits": payload_bits,
                    "basis": "persisted aggregate output-event metrics",
                }
                for symbol_index, payload_bits in zip(received, decoded)
            )
        plt.xlabel("receivedSymbolIndex")
        plt.ylabel("cumulativeDecodedPayloadBits")
        plt.title(f"{rate} Soft continuous output progress")
        plt.grid(True, alpha=0.25)
        plt.legend()
        save(
            f"stage14_{rate.lower()}_continuous_output_progress",
            pd.DataFrame(rows),
            manifest,
        )


def plot_boundary(offsets: pd.DataFrame, manifest: list[dict]) -> None:
    soft = offsets[offsets.decisionMode == "Soft Float"].copy()
    for rate in RATES:
        part = soft[soft.rateCase == rate]
        grouped = (
            part.groupby(["organization", "relativeOffset"], as_index=False)[
                ["bitErrors", "bits"]
            ]
            .sum()
        )
        grouped["BER"] = grouped.bitErrors / grouped.bits
        plt.figure(figsize=(7.6, 4.8))
        for organization in ORGANIZATIONS[1:]:
            group = grouped[grouped.organization == organization]
            plt.semilogy(
                group.relativeOffset,
                group.BER.clip(lower=1e-8),
                marker="o",
                label=LABELS[organization],
            )
        plt.xlabel("Relative offset from slot boundary")
        plt.ylabel("BER")
        plt.title(f"{rate} Soft boundary-relative BER")
        plt.grid(True, which="both", alpha=0.25)
        plt.legend()
        save(
            f"stage14_{rate.lower()}_boundary_relative_ber",
            grouped,
            manifest,
        )


def write_documents(data: pd.DataFrame, manifest: list[dict]) -> None:
    soft = data[data.decisionMode == "Soft Float"]
    hard = data[data.decisionMode == "Hard"]
    rows = []
    for decision, part in (("Soft", soft), ("Hard", hard)):
        nearest = part.loc[(part.FER - 0.1).abs().groupby(
            [part.rateCase, part.organization]
        ).idxmin()]
        rows.append(
            f"- {decision}: FER≈0.1 附近的 BER 范围 "
            f"{nearest.BER.min():.3g} 到 {nearest.BER.max():.3g}，"
            f"归一化有效吞吐范围 {nearest.normalizedGoodput.min():.3g} 到 "
            f"{nearest.normalizedGoodput.max():.3g}。"
        )
    summary = representative(data, "Soft Float")
    first_min = summary.loc[summary.firstOutputDelaySymbols.idxmin()]
    first_max = summary.loc[summary.firstOutputDelaySymbols.idxmax()]
    boundary = soft[soft.organization != "A_BLOCK_300"]
    text = f"""# Stage14 正式结果分析

本轮复用 372 行 Soft Float 正式结果，仅新增 372 行 Hard 正式结果；统一表共
744 行，覆盖 2 种判决、3 种码率、4 种组织方式和每 case 31 个 Es/N0 点。

## BER、FER 与有效吞吐

{chr(10).join(rows)}

对应 12 张分判决、分码率 BER/FER 图，以及
`stage14_soft_goodput_by_rate_and_organization.png` 和
`stage14_hard_goodput_by_rate_and_organization.png`。同一组织下 Soft 通常以更低
Es/N0 达到相同 FER。当前 50x6、100x3、150x2 的 BER/FER 在每个 SNR 点完全
重合，因为三者最终使用相同接收序列和滑窗边界；它们的首次输出和 P95 时延因
slot 到达时刻不同而不重合。限制：曲线只代表 -5 至 10 dB、0.5 dB 步长的离散
BPSK-AWGN 仿真。

## 时延

Soft 的最早首次输出为 {first_min.firstOutputDelaySymbols:.0f} symbols
（{first_min.rateCase}/{LABELS[first_min.organization]}），最晚为
{first_max.firstOutputDelaySymbols:.0f} symbols
（{first_max.rateCase}/{LABELS[first_max.organization]}）。平均与 P95 决策时延见
`stage14_soft_avg_p95_decision_latency.png` 和
`stage14_hard_avg_p95_decision_latency.png`；每张图的源数据均在
`figure_data/`。限制：CPU 时间依赖本机 Release 构建，符号时延不依赖主机速度。

## 缓存与计算量

Soft 连续方案的峰值接收缓存范围为
{summary[summary.organization != "A_BLOCK_300"].peakRxBufferSymbols.min():.0f}
到 {summary[summary.organization != "A_BLOCK_300"].peakRxBufferSymbols.max():.0f}
symbols，总内存范围为
{summary.totalMemoryBytes.min():.0f} 到 {summary.totalMemoryBytes.max():.0f}
bytes。2x2 图分别展示缓存、总内存、ACS 与回溯操作，避免混用量纲。

## 连续输出与边界

三张连续输出图基于正式 CSV 持久化的首次输出、末次输出和输出批次数重建代表性
阶梯节奏；它们展示调度节奏，不是额外 Soft 正式仿真。正式连续方案共有
{int(boundary.windowTriggerCount.sum())} 次窗口触发记录。三张边界图按 offset 汇总
已有 Soft bitErrors/bits；Block300 明确为 `NOT_APPLICABLE`。边界统计受各 SNR
错误数量影响，应结合置信区间理解，不能把微小差异解释为确定恶化。
"""
    sections = ["", "## 逐图数值说明", ""]
    for item in manifest:
        figure = pd.read_csv(RESULTS / item["figureData"])
        numeric = figure.select_dtypes(include=[np.number])
        usable = [
            column
            for column in numeric.columns
            if numeric[column].notna().any()
        ]
        first = usable[0]
        second = usable[1] if len(usable) > 1 else usable[0]
        sections.extend(
            [
                f"### {item['plot']}",
                "",
                f"![{item['plot']}]({item['plot']})",
                "",
                f"源数据 {item['rows']} 行；`{first}` 范围 "
                f"{numeric[first].min():.6g} 到 {numeric[first].max():.6g}，"
                f"`{second}` 范围 {numeric[second].min():.6g} 到 "
                f"{numeric[second].max():.6g}。结论：该图按标题所示维度比较"
                "正式观测值，不混入其他判决或码率。限制：只在已运行 SNR 网格、"
                "组织配置和本机计时条件内解释。",
                "",
            ]
        )
    text += "\n".join(sections)
    (RESULTS / "results_analysis.md").write_text(text, encoding="utf-8")
    readme = """Stage14：整块与真实在线时隙组织对比

正式统一结果：results/stage14_online_slot_formal_results_all_decisions.csv
Hard 结果：results/stage14_online_slot_formal_results_hard.csv
Soft 结果：results/stage14_online_slot_formal_results_soft.csv

组织方式：A_BLOCK_300、B_CONT_50x6、C_CONT_100x3、D_CONT_150x2。
判决方式：Hard、Soft Float。码率：R12、R23、R34。
SNR = Es/N0：-5.0 至 10.0 dB，步长 0.5 dB。
停止条件：至少 1000 帧且达到 200 个帧错误，否则最多 50000 帧。

Block300 使用完整 Viterbi。连续方案保持编码器状态和打孔相位跨 slot 连续，
由 slot 到达更新接收缓存并触发真滑窗译码，最后统一终止。
"""
    (STAGE / "readme.txt").write_text(readme, encoding="utf-8")
    (RESULTS / "plot_manifest.json").write_text(
        json.dumps({"plots": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    configure_font()
    RESULTS.mkdir(exist_ok=True)
    FIGURE_DATA.mkdir(exist_ok=True)
    soft, hard, data, offsets = load_formal()
    validate(data)
    soft.to_csv(
        RESULTS / "stage14_online_slot_formal_results_soft.csv", index=False
    )
    hard.to_csv(
        RESULTS / "stage14_online_slot_formal_results_hard.csv", index=False
    )
    data.to_csv(
        RESULTS / "stage14_online_slot_formal_results_all_decisions.csv",
        index=False,
    )
    offsets.to_csv(
        RESULTS / "stage14_boundary_offset_results_all_decisions.csv",
        index=False,
    )
    manifest: list[dict] = []
    plot_error_curves(data, manifest)
    plot_goodput(data, manifest)
    plot_latency_and_compute(data, manifest)
    plot_progress(data, manifest)
    plot_boundary(offsets, manifest)
    write_documents(data, manifest)
    print(
        f"PASS_STAGE14_FINAL_DELIVERY hard={len(hard)} soft={len(soft)} "
        f"all={len(data)} plots={len(manifest)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
