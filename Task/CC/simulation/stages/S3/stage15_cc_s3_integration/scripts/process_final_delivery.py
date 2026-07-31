#!/usr/bin/env python3
"""Rebuild the final CC S3 matrix, focused figures and fair recommendations."""

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
S3 = STAGE.parent
RESULTS = STAGE / "results"
FIGURE_DATA = RESULTS / "figure_data"
RATES = ["R12", "R23", "R34"]
ORGS = [
    "A_BLOCK_300",
    "B_CONT_50x6",
    "C_CONT_100x3",
    "D_CONT_150x2",
]
ORG_LABEL = {
    "A_BLOCK_300": "Block300",
    "B_CONT_50x6": "50x6",
    "C_CONT_100x3": "100x3",
    "D_CONT_150x2": "150x2",
}
FIELDS = [
    "schemeId",
    "rate",
    "decisionMode",
    "quantMode",
    "quantBits",
    "tracebackMode",
    "dtb",
    "window",
    "slide",
    "organization",
    "snrDb",
    "actualRate",
    "frames",
    "bitErrors",
    "frameErrors",
    "BER",
    "FER",
    "berCiLow",
    "berCiHigh",
    "ferCiLow",
    "ferCiHigh",
    "normalizedGoodput",
    "firstOutputDelaySymbols",
    "avgDecisionDelaySymbols",
    "p95DecisionDelaySymbols",
    "fullFrameLastDecisionSymbol",
    "avgDecodeTimeUs",
    "p95DecodeTimeUs",
    "inputMemoryBytes",
    "survivorMemoryBytes",
    "pathMetricMemoryBytes",
    "totalMemoryBytes",
    "peakRxBufferSymbols",
    "ACSCount",
    "tracebackOperations",
    "windowTriggerCount",
    "sourceStage",
    "sourceCsv",
    "sourceRowId",
    "sourceHash",
]


def configure_font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(row: pd.Series, *names: str) -> object:
    for name in names:
        item = row.get(name, np.nan)
        if not pd.isna(item):
            return item
    return np.nan


def append(
    rows: list[dict],
    data: pd.DataFrame,
    source: Path,
    stage_name: str,
    mapper,
) -> None:
    digest = sha256(source)
    relative = source.relative_to(S3).as_posix()
    for index, row in data.iterrows():
        item = {field: np.nan for field in FIELDS}
        item.update(mapper(row))
        item.update(
            {
                "sourceStage": stage_name,
                "sourceCsv": relative,
                "sourceRowId": value(
                    row, "rowId", "caseId", "mergedRowId"
                ),
                "sourceHash": digest,
            }
        )
        if pd.isna(item["sourceRowId"]):
            item["sourceRowId"] = f"{stage_name}-{index}"
        rows.append(item)


def build_matrix() -> pd.DataFrame:
    rows: list[dict] = []

    source09 = (
        S3
        / "stage09_awgn_formal"
        / "results"
        / "stage09_two_level_merged_point_results.csv"
    )
    data09 = pd.read_csv(source09)

    def map09(row: pd.Series) -> dict:
        rate = row.caseId.split("-")[2]
        hard = row.caseId.endswith("-H")
        return {
            "schemeId": f"{rate}_BLOCK_{'HARD' if hard else 'SOFT_FLOAT'}",
            "rate": rate,
            "decisionMode": "Hard" if hard else "Soft Float",
            "quantMode": "Hard" if hard else "Float",
            "quantBits": 1 if hard else "Float",
            "tracebackMode": "Full traceback",
            "dtb": 306,
            "window": 306,
            "slide": 300,
            "organization": "A_BLOCK_300",
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.framesProcessed,
            "bitErrors": row.payloadBitErrors,
            "frameErrors": row.payloadErrorFrames,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.normalizedGoodput,
            "avgDecodeTimeUs": row.avgDecodeTime_us,
            "p95DecodeTimeUs": row.p95DecodeTime_us,
        }

    append(rows, data09, source09, "Stage09", map09)

    source10 = (
        S3
        / "stage10_traceback_study"
        / "results"
        / "stage10_traceback_study_results.csv"
    )
    data10 = pd.read_csv(source10)
    data10 = data10[data10.targetFerLevel == "FER_010"]

    def map10(row: pd.Series) -> dict:
        block = row["mode"] == "BLOCK_FULL_TRACEBACK"
        return {
            "schemeId": (
                f"{row.rateCase}_TRACEBACK_BLOCK"
                if block
                else f"{row.rateCase}_TRACEBACK_D{int(row.dtb)}"
            ),
            "rate": row.rateCase,
            "decisionMode": "Soft Float",
            "quantMode": "Float",
            "quantBits": "Float",
            "tracebackMode": row["mode"],
            "dtb": int(row.dtb),
            "window": 306 if block else int(row.dtb),
            "slide": 300 if block else 1,
            "organization": "A_BLOCK_300" if block else "Continuous300",
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.frames,
            "bitErrors": row.bitErrors,
            "frameErrors": row.frameErrors,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.actualRate * (1 - row.FER),
            "firstOutputDelaySymbols": row.firstDecisionDelaySymbols,
            "avgDecisionDelaySymbols": row.avgDecisionDelaySymbols,
            "p95DecisionDelaySymbols": row.p95DecisionDelaySymbols,
            "avgDecodeTimeUs": row.avgDecodeTimeUs,
            "p95DecodeTimeUs": row.p95DecodeTimeUs,
            "survivorMemoryBytes": row.survivorMemoryBytes,
            "pathMetricMemoryBytes": row.pathMetricMemoryBytes,
            "totalMemoryBytes": row.totalDecoderMemoryBytes,
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
        }

    append(rows, data10, source10, "Stage10", map10)

    source11 = (
        S3
        / "stage11_soft_quantization"
        / "results"
        / "stage11_soft_quantization_results.csv"
    )
    data11 = pd.read_csv(source11)
    data11 = data11[data11.quantMode.isin(["Float", "Q4", "Q6", "Q8"])]

    def map11(row: pd.Series) -> dict:
        quantized = row.quantMode != "Float"
        return {
            "schemeId": f"{row.rateCase}_BLOCK_{row.quantMode.upper()}",
            "rate": row.rateCase,
            "decisionMode": "Soft Quantized" if quantized else "Soft Float",
            "quantMode": row.quantMode,
            "quantBits": row.quantBits,
            "tracebackMode": "Full traceback",
            "dtb": 306,
            "window": 306,
            "slide": 300,
            "organization": "A_BLOCK_300",
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.frames,
            "bitErrors": row.bitErrors,
            "frameErrors": row.frameErrors,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.actualRate * (1 - row.FER),
            "avgDecodeTimeUs": row.avgDecodeTimeUs,
            "p95DecodeTimeUs": row.p95DecodeTimeUs,
            "inputMemoryBytes": row.inputMemoryBytes,
            "survivorMemoryBytes": row.survivorMemoryBytes,
            "pathMetricMemoryBytes": row.pathMetricMemoryBytes,
            "totalMemoryBytes": row.totalDecoderMemoryBytes,
        }

    append(rows, data11, source11, "Stage11", map11)

    source13 = (
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_final_comparison.csv"
    )
    data13 = pd.read_csv(source13)

    def map13(row: pd.Series) -> dict:
        block = row.comparisonMode == "BLOCK_FULL_TRACEBACK"
        return {
            "schemeId": f"{row.rateCase}_{row.comparisonMode}",
            "rate": row.rateCase,
            "decisionMode": "Soft Float",
            "quantMode": "Float",
            "quantBits": "Float",
            "tracebackMode": row.comparisonMode,
            "dtb": row.dtb,
            "window": row.windowBits,
            "slide": row.slideBits,
            "organization": "A_BLOCK_300" if block else "Continuous300",
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.frames,
            "bitErrors": row.bitErrors,
            "frameErrors": row.frameErrors,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.actualRate * (1 - row.FER),
            "firstOutputDelaySymbols": row.firstOutputDelaySymbols,
            "avgDecisionDelaySymbols": row.avgDecisionDelaySymbols,
            "p95DecisionDelaySymbols": row.p95DecisionDelaySymbols,
            "fullFrameLastDecisionSymbol": row.fullFrameLastDecisionSymbol,
            "avgDecodeTimeUs": value(
                row, "avgDecodeTimeUs", "avgWindowProcessingTimeUs"
            ),
            "p95DecodeTimeUs": value(
                row, "p95DecodeTimeUs", "p95WindowProcessingTimeUs"
            ),
            "survivorMemoryBytes": row.survivorMemoryBytes,
            "pathMetricMemoryBytes": row.pathMetricMemoryBytes,
            "totalMemoryBytes": row.totalMemoryBytes,
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
            "windowTriggerCount": row.windowTriggerCount,
        }

    append(rows, data13, source13, "Stage13", map13)

    source13_full = (
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_full_wsd_formal_results.csv"
    )
    data13_full = pd.read_csv(source13_full)

    def map13_full(row: pd.Series) -> dict:
        return {
            "schemeId": (
                f"{row.rateCase}_{row.experimentId}_W{int(row.windowBits)}"
                f"_S{int(row.slideBits)}_D{int(row.dtb)}"
            ),
            "rate": row.rateCase,
            "decisionMode": "Soft Float",
            "quantMode": "Float",
            "quantBits": "Float",
            "tracebackMode": "True sliding-window",
            "dtb": row.dtb,
            "window": row.windowBits,
            "slide": row.slideBits,
            "organization": "Continuous300",
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.frames,
            "bitErrors": row.bitErrors,
            "frameErrors": row.frameErrors,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.normalizedGoodput,
            "firstOutputDelaySymbols": row.firstOutputDelaySymbols,
            "avgDecisionDelaySymbols": row.avgDecisionDelaySymbols,
            "p95DecisionDelaySymbols": row.p95DecisionDelaySymbols,
            "fullFrameLastDecisionSymbol": row.fullFrameLastDecisionSymbol,
            "avgDecodeTimeUs": row.avgWindowProcessingTimeUs,
            "p95DecodeTimeUs": row.p95WindowProcessingTimeUs,
            "survivorMemoryBytes": row.survivorMemoryBytes,
            "pathMetricMemoryBytes": row.pathMetricMemoryBytes,
            "totalMemoryBytes": row.totalMemoryBytes,
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
            "windowTriggerCount": row.windowTriggerCount,
        }

    append(rows, data13_full, source13_full, "Stage13FullWSD", map13_full)

    source14 = (
        S3
        / "stage14_block_continuous_comparison"
        / "results"
        / "stage14_online_slot_formal_results_all_decisions.csv"
    )
    data14 = pd.read_csv(source14)

    def map14(row: pd.Series) -> dict:
        block = row.organization == "A_BLOCK_300"
        return {
            "schemeId": (
                f"{row.rateCase}_{row.decisionMode.replace(' ', '_').upper()}_"
                f"{row.organization}"
            ),
            "rate": row.rateCase,
            "decisionMode": row.decisionMode,
            "quantMode": "Hard" if row.decisionMode == "Hard" else "Float",
            "quantBits": 1 if row.decisionMode == "Hard" else "Float",
            "tracebackMode": (
                "Full traceback" if block else "True sliding-window"
            ),
            "dtb": row.dtb,
            "window": row.windowBits,
            "slide": row.slideBits,
            "organization": row.organization,
            "snrDb": row.snrDb,
            "actualRate": row.actualRate,
            "frames": row.frames,
            "bitErrors": row.bitErrors,
            "frameErrors": row.frameErrors,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.normalizedGoodput,
            "firstOutputDelaySymbols": row.firstOutputDelaySymbols,
            "avgDecisionDelaySymbols": row.avgDecisionDelaySymbols,
            "p95DecisionDelaySymbols": row.p95DecisionDelaySymbols,
            "fullFrameLastDecisionSymbol": row.fullFrameLastDecisionSymbol,
            "avgDecodeTimeUs": row.avgDecodeTimeUs,
            "p95DecodeTimeUs": row.p95DecodeTimeUs,
            "totalMemoryBytes": row.totalMemoryBytes,
            "peakRxBufferSymbols": row.peakRxBufferSymbols,
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
            "windowTriggerCount": row.windowTriggerCount,
        }

    append(rows, data14, source14, "Stage14", map14)
    matrix = pd.DataFrame(rows, columns=FIELDS)
    matrix.to_csv(RESULTS / "stage15_final_scheme_matrix.csv", index=False)
    return matrix


def figure_data(name: str, data: pd.DataFrame) -> Path:
    path = FIGURE_DATA / f"{name}.csv"
    data.to_csv(path, index=False)
    if data.empty:
        raise RuntimeError(f"empty figure data: {name}")
    return path


def save(
    name: str, data: pd.DataFrame, manifest: list[dict]
) -> None:
    source = figure_data(name, data)
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


def plot_rate_curves(
    data: pd.DataFrame,
    metric: str,
    title: str,
    name: str,
    manifest: list[dict],
) -> None:
    plt.figure(figsize=(7.6, 5.0))
    for rate in RATES:
        group = data[data.rate == rate].sort_values("snrDb")
        plt.semilogy(
            group.snrDb,
            group[metric].clip(lower=1e-8),
            marker="o",
            markersize=3,
            linewidth=1.2,
            label=rate,
        )
    plt.xlabel("SNR = Es/N0 (dB)")
    plt.ylabel(metric)
    plt.title(title)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    save(name, data, manifest)


def plot_block(matrix: pd.DataFrame, manifest: list[dict]) -> None:
    block = matrix[
        (matrix.sourceStage == "Stage09")
        & (matrix.organization == "A_BLOCK_300")
    ].drop_duplicates(["schemeId", "snrDb"])
    soft = block[block.decisionMode == "Soft Float"]
    plot_rate_curves(
        soft,
        "BER",
        "Block300 Float Soft BER by rate",
        "stage15_block_soft_ber_by_rate",
        manifest,
    )
    plot_rate_curves(
        soft,
        "FER",
        "Block300 Float Soft FER by rate",
        "stage15_block_soft_fer_by_rate",
        manifest,
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    for axis, rate in zip(axes, RATES):
        for decision in ("Hard", "Soft Float"):
            group = block[
                (block.rate == rate) & (block.decisionMode == decision)
            ].sort_values("snrDb")
            axis.semilogy(
                group.snrDb,
                group.FER.clip(lower=1e-8),
                marker="o",
                markersize=3,
                label=decision,
            )
        axis.set_title(rate)
        axis.set_xlabel("SNR = Es/N0 (dB)")
        axis.grid(True, which="both", alpha=0.25)
    axes[0].set_ylabel("FER")
    axes[-1].legend()
    fig.suptitle("Block300 Hard versus Float Soft")
    save("stage15_block_hard_soft_fer", block, manifest)


def stage14_rows(matrix: pd.DataFrame, decision: str) -> pd.DataFrame:
    return matrix[
        (matrix.sourceStage == "Stage14")
        & (matrix.decisionMode == decision)
    ].drop_duplicates(["schemeId", "snrDb"])


def plot_slot_curves(
    matrix: pd.DataFrame, manifest: list[dict]
) -> None:
    for decision, token in (("Soft Float", "soft"), ("Hard", "hard")):
        data = stage14_rows(matrix, decision)
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
        for axis, rate in zip(axes, RATES):
            for organization in ORGS:
                group = data[
                    (data.rate == rate)
                    & (data.organization == organization)
                ].sort_values("snrDb")
                axis.semilogy(
                    group.snrDb,
                    group.FER.clip(lower=1e-8),
                    marker="o",
                    markersize=2.5,
                    linewidth=1,
                    label=ORG_LABEL[organization],
                )
            axis.set_title(rate)
            axis.set_xlabel("SNR = Es/N0 (dB)")
            axis.grid(True, which="both", alpha=0.25)
        axes[0].set_ylabel("FER")
        axes[-1].legend(fontsize=8)
        fig.suptitle(f"Stage14 {decision}: slot organization FER")
        save(f"stage15_slot_{token}_fer", data, manifest)

    soft = stage14_rows(matrix, "Soft Float")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    for axis, rate in zip(axes, RATES):
        for organization in ORGS:
            group = soft[
                (soft.rate == rate) & (soft.organization == organization)
            ].sort_values("snrDb")
            axis.plot(
                group.snrDb,
                group.normalizedGoodput,
                marker="o",
                markersize=2.5,
                linewidth=1,
                label=ORG_LABEL[organization],
            )
        axis.set_title(rate)
        axis.set_xlabel("SNR = Es/N0 (dB)")
        axis.grid(True, alpha=0.25)
    axes[0].set_ylabel("Normalized goodput")
    axes[-1].legend(fontsize=8)
    fig.suptitle("Stage14 Float Soft normalized goodput")
    save("stage15_slot_soft_goodput", soft, manifest)


def slot_summary(matrix: pd.DataFrame) -> pd.DataFrame:
    data = matrix[matrix.sourceStage == "Stage14"].copy()
    metrics = [
        "firstOutputDelaySymbols",
        "avgDecisionDelaySymbols",
        "p95DecisionDelaySymbols",
        "peakRxBufferSymbols",
        "totalMemoryBytes",
        "avgDecodeTimeUs",
    ]
    return data.groupby(
        ["decisionMode", "rate", "organization"], as_index=False
    )[metrics].median()


def plot_slot_latency(matrix: pd.DataFrame, manifest: list[dict]) -> None:
    summary = slot_summary(matrix)
    x = np.arange(len(ORGS))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for axis, decision in zip(axes, ("Soft Float", "Hard")):
        for rate in RATES:
            group = summary[
                (summary.decisionMode == decision) & (summary.rate == rate)
            ].set_index("organization").reindex(ORGS)
            axis.plot(
                x, group.firstOutputDelaySymbols, marker="o", label=rate
            )
        axis.set_xticks(x, [ORG_LABEL[item] for item in ORGS])
        axis.set_title(decision)
        axis.grid(True, alpha=0.25)
    axes[0].set_ylabel("First output delay (symbols)")
    axes[-1].legend()
    fig.suptitle("Slot first-output latency")
    save("stage15_slot_first_output_latency", summary, manifest)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    soft = summary[summary.decisionMode == "Soft Float"]
    for axis, rate in zip(axes, RATES):
        group = soft[soft.rate == rate].set_index(
            "organization"
        ).reindex(ORGS)
        axis.bar(
            x - 0.18, group.avgDecisionDelaySymbols, 0.36, label="Avg"
        )
        axis.bar(
            x + 0.18, group.p95DecisionDelaySymbols, 0.36, label="P95"
        )
        axis.set_xticks(x, [ORG_LABEL[item] for item in ORGS])
        axis.set_title(rate)
        axis.grid(True, axis="y", alpha=0.25)
    axes[0].set_ylabel("Decision delay (symbols)")
    axes[-1].legend()
    fig.suptitle("Float Soft average and P95 slot decision latency")
    save("stage15_slot_avg_p95_latency", soft, manifest)


def plot_quantization(manifest: list[dict]) -> None:
    path = (
        S3
        / "stage11_soft_quantization"
        / "results"
        / "stage11_quantization_snr_loss.csv"
    )
    data = pd.read_csv(path)
    data = data[
        data.quantMode.isin(["Q3", "Q4", "Q5", "Q6", "Q7", "Q8"])
        & np.isclose(data.targetFer, 0.1)
    ]
    plt.figure(figsize=(8, 4.8))
    for rate in RATES:
        group = data[data.rateCase == rate]
        plt.plot(
            group.quantMode,
            group.snrLossVsFloat,
            marker="o",
            label=rate,
        )
    plt.xlabel("Quantization mode")
    plt.ylabel("SNR loss versus Float (dB)")
    plt.title("Quantization loss at FER=0.1")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_quantization_snr_loss", data, manifest)


def plot_traceback(manifest: list[dict]) -> pd.DataFrame:
    path = (
        S3
        / "stage10_traceback_study"
        / "results"
        / "stage10_traceback_study_results.csv"
    )
    raw = pd.read_csv(path)
    print(
        "STAGE10_FILTER "
        f"rows={len(raw)} "
        f"targetFerLevel={sorted(raw.targetFerLevel.unique())} "
        f"mode={sorted(raw['mode'].unique())} "
        f"dtb={sorted(raw.dtb.unique())}"
    )
    data = raw[
        (raw.targetFerLevel == "FER_010")
        & (raw["mode"] == "CONTINUOUS_TRUNCATED_VITERBI")
        & raw.dtb.isin([35, 49, 70, 84, 98, 112])
    ].copy()
    if len(data) != 18:
        raise RuntimeError(f"traceback figure points={len(data)}, expected 18")
    plt.figure(figsize=(8, 5.0))
    for rate in RATES:
        group = data[data.rateCase == rate]
        plt.scatter(
            group.totalDecoderMemoryBytes,
            group.relativeFerIncreaseVsBlock,
            label=rate,
        )
        for _, row in group.iterrows():
            plt.annotate(
                f"D{int(row.dtb)}",
                (
                    row.totalDecoderMemoryBytes,
                    row.relativeFerIncreaseVsBlock,
                ),
                fontsize=7,
            )
    plt.xlabel("Total decoder memory (bytes)")
    plt.ylabel("Relative FER increase versus block")
    plt.title("Traceback memory-reliability tradeoff at FER=0.1")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_traceback_memory_reliability", data, manifest)
    return data


def plot_sliding_summary(manifest: list[dict]) -> None:
    path = (
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_full_wsd_formal_results.csv"
    )
    data = pd.read_csv(path)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    specifications = [
        (
            "CONTROL_W",
            "windowBits",
            "firstOutputDelaySymbols",
            "W: first output; fixed S16/D70",
        ),
        (
            "CONTROL_S",
            "slideBits",
            "p95DecisionDelaySymbols",
            "S: P95 delay; fixed W160/D70",
        ),
        (
            "CONTROL_D",
            "dtb",
            "relativeFerIncreaseVsBlock",
            "D: relative FER; fixed W160/S16",
        ),
    ]
    selected_rows = []
    for axis, (experiment, xcol, ycol, title) in zip(axes, specifications):
        part = data[data.experimentId == experiment]
        summary = part.groupby(["rateCase", xcol], as_index=False)[
            ycol
        ].median()
        selected_rows.append(
            summary.assign(experimentId=experiment, metric=ycol)
        )
        for rate in RATES:
            group = summary[summary.rateCase == rate]
            axis.plot(group[xcol], group[ycol], marker="o", label=rate)
        axis.set_xlabel(xcol)
        axis.set_ylabel(ycol)
        axis.set_title(title)
        axis.grid(True, alpha=0.25)
    axes[-1].legend()
    save(
        "stage15_sliding_parameter_summary",
        pd.concat(selected_rows, ignore_index=True),
        manifest,
    )


def interpolation_at_fer(
    group: pd.DataFrame, target: float = 0.1
) -> dict | None:
    group = group.sort_values("snrDb").drop_duplicates("snrDb")
    positive = group[group.FER > 0].copy()
    if positive.empty or not (
        positive.FER.max() >= target >= positive.FER.min()
    ):
        return None
    for (_, low), (_, high) in zip(
        positive.iloc[:-1].iterrows(), positive.iloc[1:].iterrows()
    ):
        if (low.FER - target) * (high.FER - target) <= 0:
            if np.isclose(low.FER, high.FER):
                fraction = 0.0
            else:
                fraction = (
                    np.log(target) - np.log(low.FER)
                ) / (np.log(high.FER) - np.log(low.FER))
            result = {
                "snrAtFer01": low.snrDb
                + fraction * (high.snrDb - low.snrDb),
                "coveredByData": True,
            }
            for column in [
                "firstOutputDelaySymbols",
                "avgDecisionDelaySymbols",
                "p95DecisionDelaySymbols",
                "totalMemoryBytes",
                "avgDecodeTimeUs",
                "tracebackOperations",
                "normalizedGoodput",
            ]:
                first = pd.to_numeric(low[column], errors="coerce")
                second = pd.to_numeric(high[column], errors="coerce")
                result[column] = (
                    first + fraction * (second - first)
                    if not pd.isna(first) and not pd.isna(second)
                    else np.nan
                )
            return result
    return None


def candidate_curves(matrix: pd.DataFrame) -> pd.DataFrame:
    stage14 = matrix[matrix.sourceStage == "Stage14"].copy()
    block = matrix[
        (matrix.sourceStage == "Stage09")
        & matrix.schemeId.str.contains("BLOCK")
    ].copy()
    stage13 = matrix[
        (matrix.sourceStage == "Stage13")
        & matrix.tracebackMode.isin(
            ["SLIDING_BALANCED", "SLIDING_LATENCY_FIRST"]
        )
    ].copy()
    return pd.concat([block, stage13, stage14], ignore_index=True).drop_duplicates(
        ["schemeId", "snrDb"]
    )


def build_operating_points(matrix: pd.DataFrame) -> pd.DataFrame:
    curves = candidate_curves(matrix)
    rows = []
    for scheme, group in curves.groupby("schemeId"):
        base = group.iloc[0]
        target = interpolation_at_fer(group)
        if target is None:
            rows.append(
                {
                    "schemeId": scheme,
                    "rate": base.rate,
                    "decisionMode": base.decisionMode,
                    "organization": base.organization,
                    "comparisonBasis": "fixed_target_fer",
                    "targetFer": 0.1,
                    "fixedSnrDb": np.nan,
                    "coveredByData": False,
                    "exclusionReason": "FER=0.1 is not bracketed by real points",
                }
            )
        else:
            rows.append(
                {
                    "schemeId": scheme,
                    "rate": base.rate,
                    "decisionMode": base.decisionMode,
                    "organization": base.organization,
                    "comparisonBasis": "fixed_target_fer",
                    "targetFer": 0.1,
                    "fixedSnrDb": np.nan,
                    "FER": 0.1,
                    "exclusionReason": "",
                    **target,
                }
            )
        exact = group[np.isclose(group.snrDb, 2.0)]
        if not exact.empty:
            point = exact.iloc[0]
            rows.append(
                {
                    "schemeId": scheme,
                    "rate": point.rate,
                    "decisionMode": point.decisionMode,
                    "organization": point.organization,
                    "comparisonBasis": "fixed_snr",
                    "targetFer": np.nan,
                    "fixedSnrDb": 2.0,
                    "coveredByData": True,
                    "snrAtFer01": np.nan,
                    "FER": point.FER,
                    "BER": point.BER,
                    "normalizedGoodput": point.normalizedGoodput,
                    "firstOutputDelaySymbols": point.firstOutputDelaySymbols,
                    "avgDecisionDelaySymbols": point.avgDecisionDelaySymbols,
                    "p95DecisionDelaySymbols": point.p95DecisionDelaySymbols,
                    "totalMemoryBytes": point.totalMemoryBytes,
                    "avgDecodeTimeUs": point.avgDecodeTimeUs,
                    "tracebackOperations": point.tracebackOperations,
                    "exclusionReason": "",
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(RESULTS / "stage15_fair_operating_points.csv", index=False)
    return result


def recommendations(points: pd.DataFrame) -> pd.DataFrame:
    choices = []

    def select(
        kind: str,
        basis: str,
        required: list[str],
        score,
        reason: str,
    ) -> None:
        data = points[
            (points.comparisonBasis == basis)
            & (points.coveredByData == True)
        ].copy()
        data = data.dropna(subset=required)
        if data.empty:
            raise RuntimeError(f"no eligible candidates for {kind}")
        row = score(data)
        choices.append(
            {
                "recommendationType": kind,
                "schemeId": row.schemeId,
                "rate": row.rate,
                "decisionMode": row.decisionMode,
                "organization": row.organization,
                "comparisonBasis": basis,
                "targetFer": 0.1 if basis == "fixed_target_fer" else np.nan,
                "fixedSnrDb": 2.0 if basis == "fixed_snr" else np.nan,
                "coveredByData": True,
                "snrAtFer01": value(row, "snrAtFer01"),
                "FER": value(row, "FER"),
                "normalizedGoodput": value(row, "normalizedGoodput"),
                "firstOutputDelaySymbols": value(
                    row, "firstOutputDelaySymbols"
                ),
                "totalMemoryBytes": value(row, "totalMemoryBytes"),
                "avgDecodeTimeUs": value(row, "avgDecodeTimeUs"),
                "selectionReason": reason,
                "exclusionReason": "",
            }
        )

    select(
        "reliability_first",
        "fixed_snr",
        ["FER"],
        lambda data: data.loc[data.FER.idxmin()],
        "At Es/N0=2.0 dB, minimize measured FER.",
    )
    select(
        "throughput_first",
        "fixed_snr",
        ["normalizedGoodput"],
        lambda data: data.loc[data.normalizedGoodput.idxmax()],
        "At Es/N0=2.0 dB, maximize normalized goodput.",
    )
    select(
        "latency_first",
        "fixed_target_fer",
        ["firstOutputDelaySymbols", "snrAtFer01"],
        lambda data: data.loc[data.firstOutputDelaySymbols.idxmin()],
        "At interpolated FER=0.1, minimize first-output delay.",
    )
    select(
        "memory_first",
        "fixed_target_fer",
        ["totalMemoryBytes", "snrAtFer01"],
        lambda data: data.loc[data.totalMemoryBytes.idxmin()],
        "At interpolated FER=0.1, minimize total decoder memory.",
    )
    data = points[
        (points.comparisonBasis == "fixed_target_fer")
        & (points.coveredByData == True)
    ].dropna(
        subset=[
            "snrAtFer01",
            "firstOutputDelaySymbols",
            "totalMemoryBytes",
            "avgDecodeTimeUs",
        ]
    ).copy()
    if data.empty:
        raise RuntimeError("no complete candidates for balanced recommendation")
    for column in [
        "snrAtFer01",
        "firstOutputDelaySymbols",
        "totalMemoryBytes",
        "avgDecodeTimeUs",
    ]:
        low, high = data[column].min(), data[column].max()
        data[f"n_{column}"] = (
            0.0
            if np.isclose(low, high)
            else (data[column] - low) / (high - low)
        )
    data["score"] = (
        0.40 * data.n_snrAtFer01
        + 0.25 * data.n_firstOutputDelaySymbols
        + 0.20 * data.n_totalMemoryBytes
        + 0.15 * data.n_avgDecodeTimeUs
    )
    row = data.loc[data.score.idxmin()]
    choices.append(
        {
            "recommendationType": "balanced",
            "schemeId": row.schemeId,
            "rate": row.rate,
            "decisionMode": row.decisionMode,
            "organization": row.organization,
            "comparisonBasis": "fixed_target_fer",
            "targetFer": 0.1,
            "fixedSnrDb": np.nan,
            "coveredByData": True,
            "snrAtFer01": row.snrAtFer01,
            "FER": 0.1,
            "normalizedGoodput": row.normalizedGoodput,
            "firstOutputDelaySymbols": row.firstOutputDelaySymbols,
            "totalMemoryBytes": row.totalMemoryBytes,
            "avgDecodeTimeUs": row.avgDecodeTimeUs,
            "selectionReason": (
                "At interpolated FER=0.1, minimize a fixed weighted score "
                "of required SNR, first-output delay, memory and CPU time."
            ),
            "exclusionReason": "",
        }
    )
    result = pd.DataFrame(choices)
    result.to_csv(RESULTS / "stage15_final_recommendations.csv", index=False)
    return result


def plot_pareto(
    matrix: pd.DataFrame,
    points: pd.DataFrame,
    manifest: list[dict],
) -> None:
    target = points[
        (points.comparisonBasis == "fixed_target_fer")
        & (points.coveredByData == True)
    ].copy()
    selected = []
    for rate in RATES:
        block = target[
            (target.rate == rate)
            & target.schemeId.str.endswith("SOFT_FLOAT_A_BLOCK_300")
        ]
        balanced = target[
            (target.rate == rate)
            & target.schemeId.str.contains("SLIDING_BALANCED")
        ]
        slot = target[
            (target.rate == rate)
            & (target.organization == "B_CONT_50x6")
            & (target.decisionMode == "Soft Float")
        ]
        for group in (block, balanced, slot):
            if not group.empty:
                selected.append(group.iloc[0])
    data = pd.DataFrame(selected).drop_duplicates("schemeId")
    if len(data) != 9:
        raise RuntimeError(f"Pareto representative point count={len(data)}")
    plt.figure(figsize=(8.5, 5.2))
    for _, row in data.iterrows():
        plt.scatter(row.firstOutputDelaySymbols, row.snrAtFer01)
        label = (
            f"{row.rate}/"
            f"{'Block' if row.organization == 'A_BLOCK_300' else ORG_LABEL.get(row.organization, 'Balanced')}"
        )
        plt.annotate(
            label,
            (row.firstOutputDelaySymbols, row.snrAtFer01),
            fontsize=7,
        )
    plt.xlabel("First output delay (symbols)")
    plt.ylabel("Required Es/N0 at FER=0.1 (dB)")
    plt.title("Representative latency-reliability tradeoff")
    plt.grid(True, alpha=0.25)
    save("stage15_latency_reliability_pareto", data, manifest)


def at_target(points: pd.DataFrame, pattern: str) -> pd.DataFrame:
    return points[
        (points.comparisonBasis == "fixed_target_fer")
        & (points.coveredByData == True)
        & points.schemeId.str.contains(pattern, regex=True)
    ]


def write_documents(
    matrix: pd.DataFrame,
    points: pd.DataFrame,
    recs: pd.DataFrame,
    trace: pd.DataFrame,
    manifest: list[dict],
) -> None:
    block_soft = at_target(points, r"BLOCK_SOFT_FLOAT$")
    block_hard = at_target(points, r"BLOCK_HARD$")
    qloss = pd.read_csv(
        RESULTS / "figure_data" / "stage15_quantization_snr_loss.csv"
    )
    q8 = qloss[qloss.quantMode == "Q8"]
    slot = at_target(
        points,
        r"(?:A_BLOCK_300|B_CONT_50x6|C_CONT_100x3|D_CONT_150x2)$",
    )
    summary = slot_summary(matrix)
    soft_summary = summary[summary.decisionMode == "Soft Float"]
    fastest = soft_summary.loc[
        soft_summary.firstOutputDelaySymbols.idxmin()
    ]
    p95 = soft_summary.loc[soft_summary.p95DecisionDelaySymbols.idxmin()]
    memory = soft_summary.loc[soft_summary.totalMemoryBytes.idxmin()]
    d84 = trace[trace.dtb == 84].relativeFerIncreaseVsBlock.median()
    d112 = trace[trace.dtb == 112].relativeFerIncreaseVsBlock.median()
    fixed2 = points[
        (points.comparisonBasis == "fixed_snr")
        & (points.coveredByData == True)
    ]
    rate_fer = fixed2.groupby("rate").FER.min().sort_values()
    rec_lines = "\n".join(
        f"- {row.recommendationType}: `{row.schemeId}`，比较基准 "
        f"`{row.comparisonBasis}`；{row.selectionReason}"
        for _, row in recs.iterrows()
    )
    report = f"""# CC S3 最终正式报告

## 最终结论

1. 在共同 Es/N0=2.0 dB 下，按本矩阵候选的最低 FER 排序为：
   {", ".join(f"{rate}={rate_fer[rate]:.4g}" for rate in rate_fer.index)}。
   不同码率本身改变冗余度，因此这不是同吞吐条件比较。
2. Block Float Soft 在 FER=0.1 的插值 Es/N0 为：
   {", ".join(f"{row.rate}={row.snrAtFer01:.3f} dB" for _, row in block_soft.iterrows())}。
3. Block Soft 相对 Hard 的 FER=0.1 SNR 优势为：
   {", ".join(f"{rate}={float(block_hard[block_hard.rate == rate].snrAtFer01.iloc[0] - block_soft[block_soft.rate == rate].snrAtFer01.iloc[0]):.3f} dB" for rate in RATES)}。
4. 当前正式结果中 50x6、100x3、150x2 的 FER/BER 在每个 SNR 点完全重合；
   三者最终使用相同接收序列和滑窗边界，因此最终判决一致。组织方式仍改变真实
   slot 到达时刻，所以首次输出与 P95 时延并不重合。
5. Soft 首次输出最早的是 {fastest.rate}/{ORG_LABEL[fastest.organization]}，
   {fastest.firstOutputDelaySymbols:.0f} symbols。
6. Soft P95 决策时延最低的是 {p95.rate}/{ORG_LABEL[p95.organization]}，
   {p95.p95DecisionDelaySymbols:.0f} symbols。
7. 矩阵中总内存最小的 Soft 时隙代表是
   {memory.rate}/{ORG_LABEL[memory.organization]}，
   {memory.totalMemoryBytes:.0f} bytes。
8. 三种时隙的可靠性完全重合而时延不重合：编码器状态、打孔相位、滑窗边界和
   最终终止规则一致，保证最终判决一致；slot 到达粒度改变输出可用时刻。
9. W 决定窗口覆盖和缓存/首次输出，S 决定触发频率与输出节奏，D 决定回溯可靠性
   和回溯计算量。实际控制配置为 W 实验 S16/D70，S 实验 W160/D70，D 实验
   W160/S16。
10. Q8 相对 Float 在 FER=0.1 的 SNR 损失为：
    {", ".join(f"{row.rateCase}={row.snrLossVsFloat:.3f} dB" for _, row in q8.iterrows())}。
11. D112 的中位相对 FER 增幅为 {d112:.4g}，D84 为 {d84:.4g}；更深回溯保留
    更长路径历史，通常更可靠，但消耗更多存储和回溯操作。
12. 五类最终推荐如下：

{rec_lines}

## 数据与限制

Stage14 统一表包含 Hard 372 行、Soft 372 行，共 744 行。Stage13 本轮没有补跑
D126；实际 W/S/D 控制变量与最初计划略有差异，但已有数据足以支持趋势结论，
不得声称测试了未运行参数。所有 FER=0.1 结论仅在真实点覆盖目标时使用相邻点的
对数域插值；共同工作点使用 Es/N0=2.0 dB。CPU 时间仅代表本机 Release 构建。
"""
    (RESULTS / "cc_s3_final_formal_report.md").write_text(
        report, encoding="utf-8"
    )
    analysis = f"""# Stage15 结果分析

本轮最终矩阵共 {len(matrix)} 行，其中 Stage14 Hard/Soft 四组织全量纳入。
12 张核心图均有对应 `figure_data/*.csv`，没有空图。

- Block Soft BER/FER：三码率分图/分线，避免混入 W/S/D 全候选。
- Block Hard/Soft：每码率仅两条曲线，直接给出判决增益。
- Slot Soft/Hard：每码率四条组织曲线，保留 100x3 与 150x2。
- 时延图：只比较四组织和三码率；首次输出、平均与 P95 分开展示。
- 量化图：Q3 至 Q8 在 FER=0.1 的损失；Q8 范围
  {q8.snrLossVsFloat.min():.3f} 至 {q8.snrLossVsFloat.max():.3f} dB。
- 回溯图：真实筛选值为 `FER_010` 与
  `CONTINUOUS_TRUNCATED_VITERBI`，有效点恰为 {len(trace)}。
- Pareto 图只保留少量 Block Float、Stage13 balanced、50x6 Soft 代表点。

推荐先在同目标 FER=0.1 下比较所需 SNR、时延、内存和 CPU；若曲线不覆盖目标则
排除。吞吐与可靠性推荐另在固定 Es/N0=2.0 dB 比较。限制：离散点插值不替代新增
dense 仿真，且不同码率的同 SNR 比较不等价于同净吞吐比较。
"""
    figure_sections = ["", "## 十二张核心图", ""]
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
        figure_sections.extend(
            [
                f"### {item['plot']}",
                "",
                f"![{item['plot']}]({item['plot']})",
                "",
                f"figure-data 共 {item['rows']} 行；`{first}` 从 "
                f"{numeric[first].min():.6g} 到 {numeric[first].max():.6g}，"
                f"`{second}` 从 {numeric[second].min():.6g} 到 "
                f"{numeric[second].max():.6g}。结论：该图只保留标题指定的"
                "比较变量，避免候选过载。限制：只解释正式 CSV 覆盖的工作区间。",
                "",
            ]
        )
    analysis += "\n".join(figure_sections)
    (RESULTS / "results_analysis.md").write_text(
        analysis, encoding="utf-8"
    )
    readme = """Stage15：CC S3 最终集成

运行 scripts/process_final_delivery.py 复用 Stage09/10/11/13 和 Stage14 正式 CSV，
生成最终矩阵、12 张核心图、公平工作点与五类推荐。运行
scripts/check_stage15_revision.py 做实质数据检查。

最终报告：results/cc_s3_final_formal_report.md
最终矩阵：results/stage15_final_scheme_matrix.csv
推荐表：results/stage15_final_recommendations.csv
公平工作点：results/stage15_fair_operating_points.csv
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
    matrix = build_matrix()
    manifest: list[dict] = []
    plot_block(matrix, manifest)
    plot_slot_curves(matrix, manifest)
    plot_slot_latency(matrix, manifest)
    plot_quantization(manifest)
    trace = plot_traceback(manifest)
    plot_sliding_summary(manifest)
    points = build_operating_points(matrix)
    recs = recommendations(points)
    plot_pareto(matrix, points, manifest)
    write_documents(matrix, points, recs, trace, manifest)
    print(
        f"PASS_CC_S3_FINAL_PROCESS matrix={len(matrix)} "
        f"plots={len(manifest)} recommendations={len(recs)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
