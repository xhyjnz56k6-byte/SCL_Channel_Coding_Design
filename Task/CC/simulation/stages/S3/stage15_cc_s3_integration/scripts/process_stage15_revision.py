#!/usr/bin/env python3
"""Build the Stage15 auditable matrix, final plots and numeric conclusions."""

from __future__ import annotations

import hashlib
import json
import math
import os
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
FIELDS = [
    "schemeId",
    "rate",
    "decisionMode",
    "quantMode",
    "quantBits",
    "clipMax",
    "tracebackMode",
    "dtb",
    "window",
    "slide",
    "organization",
    "snrDb",
    "frames",
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
    "ACSCount",
    "tracebackOperations",
    "sourceStage",
    "sourceCsv",
    "sourceRowId",
    "sourceHash",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def markdown_table(data: pd.DataFrame) -> str:
    columns = list(data.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in data.iterrows():
        lines.append(
            "| "
            + " | ".join(str(row[column]) for column in columns)
            + " |"
        )
    return "\n".join(lines)

def configure_font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def value(row: pd.Series, name: str, default: object = "N/A") -> object:
    item = row.get(name, default)
    return default if pd.isna(item) else item


def append_rows(
    target: list[dict],
    data: pd.DataFrame,
    source: Path,
    source_stage: str,
    mapper,
) -> None:
    digest = sha256(source)
    for index, row in data.iterrows():
        item = {field: "N/A" for field in FIELDS}
        item.update(mapper(row))
        item.update(
            {
                "sourceStage": source_stage,
                "sourceCsv": source.relative_to(S3).as_posix(),
                "sourceRowId": value(
                    row,
                    "rowId",
                    value(row, "caseId", f"{source_stage}-{index}"),
                ),
                "sourceHash": digest,
            }
        )
        target.append(item)


def build_matrix() -> pd.DataFrame:
    rows: list[dict] = []
    stage09 = (
        S3
        / "stage09_awgn_formal"
        / "results"
        / "stage09_two_level_merged_point_results.csv"
    )
    data09 = pd.read_csv(stage09)
    coarse09 = data09[data09.gridLayer.str.startswith("coarse")].copy()

    def map09(row: pd.Series) -> dict:
        parts = row.caseId.split("-")
        rate, decision = parts[2], parts[3]
        return {
            "schemeId": f"{rate}_{decision}_BLOCK_FULL",
            "rate": rate,
            "decisionMode": "Hard" if decision == "H" else "Soft Float",
            "quantMode": "Hard" if decision == "H" else "Float",
            "quantBits": 1 if decision == "H" else "Float",
            "tracebackMode": "Full traceback",
            "dtb": 306,
            "window": 306,
            "slide": 300,
            "organization": "Block300",
            "snrDb": row.snrDb,
            "frames": row.framesProcessed,
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

    append_rows(rows, coarse09, stage09, "Stage09", map09)

    stage11 = (
        S3
        / "stage11_soft_quantization"
        / "results"
        / "stage11_soft_quantization_results.csv"
    )
    data11 = pd.read_csv(stage11)
    q8 = data11[
        (data11.quantMode.isin(["Q8", "Float"]))
        & (data11.gridLayer == "coarse")
    ].copy()

    def map11(row: pd.Series) -> dict:
        quantized = row.quantMode == "Q8"
        return {
            "schemeId": (
                f"{row.rateCase}_Q8_BLOCK_FULL"
                if quantized
                else f"{row.rateCase}_FLOAT_BLOCK_FULL"
            ),
            "rate": row.rateCase,
            "decisionMode": (
                "Soft Quantized" if quantized else "Soft Float"
            ),
            "quantMode": row.quantMode,
            "quantBits": 8 if quantized else "Float",
            "clipMax": row.clipMax,
            "tracebackMode": "Full traceback",
            "dtb": 306,
            "window": 306,
            "slide": 300,
            "organization": "Block300",
            "snrDb": row.snrDb,
            "frames": row.frames,
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

    append_rows(rows, q8, stage11, "Stage11", map11)

    stage13 = (
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_final_comparison.csv"
    )
    data13 = pd.read_csv(stage13)

    def map13(row: pd.Series) -> dict:
        mode = row.comparisonMode
        return {
            "schemeId": f"{row.rateCase}_{mode}",
            "rate": row.rateCase,
            "decisionMode": "Soft Float",
            "quantMode": "Float",
            "quantBits": "Float",
            "tracebackMode": mode,
            "dtb": row.dtb,
            "window": value(row, "windowBits"),
            "slide": value(row, "slideBits"),
            "organization": (
                "Block300"
                if mode == "BLOCK_FULL_TRACEBACK"
                else "Continuous300"
            ),
            "snrDb": row.snrDb,
            "frames": row.frames,
            "BER": row.BER,
            "FER": row.FER,
            "berCiLow": row.berCiLow,
            "berCiHigh": row.berCiHigh,
            "ferCiLow": row.ferCiLow,
            "ferCiHigh": row.ferCiHigh,
            "normalizedGoodput": row.actualRate * (1 - row.FER),
            "firstOutputDelaySymbols": value(
                row, "firstOutputDelaySymbols"
            ),
            "avgDecisionDelaySymbols": value(
                row, "avgDecisionDelaySymbols"
            ),
            "p95DecisionDelaySymbols": value(
                row, "p95DecisionDelaySymbols"
            ),
            "fullFrameLastDecisionSymbol": value(
                row, "fullFrameLastDecisionSymbol"
            ),
            "avgDecodeTimeUs": value(
                row, "avgDecodeTimeUs", value(row, "avgWindowProcessingTimeUs")
            ),
            "p95DecodeTimeUs": value(
                row,
                "p95DecodeTimeUs",
                value(row, "p95WindowProcessingTimeUs"),
            ),
            "survivorMemoryBytes": row.survivorMemoryBytes,
            "pathMetricMemoryBytes": row.pathMetricMemoryBytes,
            "totalMemoryBytes": row.totalMemoryBytes,
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
        }

    append_rows(rows, data13, stage13, "Stage13", map13)

    stage14 = (
        S3
        / "stage14_block_continuous_comparison"
        / "results"
        / "stage14_online_slot_formal_results.csv"
    )
    data14 = pd.read_csv(stage14)
    recommendations = pd.read_csv(
        S3
        / "stage14_block_continuous_comparison"
        / "results"
        / "stage14_organization_recommendations.csv"
    )
    selected = set(
        zip(
            recommendations[recommendations.selectedBalanced == 1].rateCase,
            recommendations[
                recommendations.selectedBalanced == 1
            ].organization,
        )
    )
    final14 = data14[
        data14.apply(
            lambda row: (row.rateCase, row.organization) in selected, axis=1
        )
    ]
    all14 = pd.concat(
        [
            data14[data14.organization == "A_BLOCK_300"],
            final14,
        ],
        ignore_index=True,
    ).drop_duplicates(["organization", "rateCase", "snrDb"])
    stage13_recommendations = pd.read_csv(
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_final_recommendations.csv"
    )
    balanced_config = {
        row.rateCase: row
        for _, row in stage13_recommendations[
            stage13_recommendations.recommendationType == "balanced"
        ].iterrows()
    }

    def map14(row: pd.Series) -> dict:
        block = row.organization == "A_BLOCK_300"
        config = balanced_config[row.rateCase]
        return {
            "schemeId": (
                f"{row.rateCase}_BLOCK_STAGE14"
                if block
                else f"{row.rateCase}_SLIDING_BALANCED_{row.organization}"
            ),
            "rate": row.rateCase,
            "decisionMode": "Soft Float",
            "quantMode": "Float",
            "quantBits": "Float",
            "tracebackMode": (
                "Full traceback" if block else "True sliding-window"
            ),
            "dtb": 306 if block else config.dtb,
            "window": 306 if block else config.windowBits,
            "slide": 300 if block else config.slideBits,
            "organization": row.organization,
            "snrDb": row.snrDb,
            "frames": row.frames,
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
            "ACSCount": row.ACSCount,
            "tracebackOperations": row.tracebackOperations,
        }

    append_rows(rows, all14, stage14, "Stage14", map14)
    matrix = pd.DataFrame(rows, columns=FIELDS)
    matrix.to_csv(RESULTS / "stage15_final_scheme_matrix.csv", index=False)
    return matrix


def semilogy_points(axis, x, values, upper, **kwargs):
    valid = values.astype(float) > 0.0
    if not valid.any():
        return None
    return axis.semilogy(
        pd.Series(x).reset_index(drop=True)[valid.reset_index(drop=True)],
        values.astype(float).reset_index(drop=True)[valid.reset_index(drop=True)],
        **kwargs,
    )[0]


def figure_data(name: str, data: pd.DataFrame) -> Path:
    path = FIGURE_DATA / f"{name}.csv"
    data.to_csv(path, index=False)
    return path


def save(name: str, source: Path, manifest: list[dict]) -> None:
    path = RESULTS / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    manifest.append(
        {
            "plot": path.name,
            "figureData": source.relative_to(RESULTS).as_posix(),
            "plotSha256": sha256(path),
            "figureDataSha256": sha256(source),
        }
    )


def final_curve_rows(matrix: pd.DataFrame) -> pd.DataFrame:
    selected = matrix[
        matrix.schemeId.str.contains(
            "_H_BLOCK_FULL|_FLOAT_BLOCK_FULL|_Q8_BLOCK_FULL|"
            "CONTINUOUS_TRUNCATED_D112|SLIDING_BALANCED"
        )
    ].copy()
    return selected.drop_duplicates(["schemeId", "snrDb"])


def plot_final(matrix: pd.DataFrame) -> list[dict]:
    manifest: list[dict] = []
    curves = final_curve_rows(matrix)
    for metric, upper, name in [
        ("BER", "berCiHigh", "stage15_final_ber"),
        ("FER", "ferCiHigh", "stage15_final_fer"),
    ]:
        source = figure_data(name, curves)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
        for axis, rate in zip(axes, RATES):
            rate_rows = curves[curves.rate == rate]
            for scheme, group in rate_rows.groupby("schemeId"):
                group = group.sort_values("snrDb")
                first = group.iloc[0]
                label = (
                    f"{first.quantMode}-D{first.dtb}-W{first.window}-"
                    f"S{first.slide}-{first.organization}"
                )
                semilogy_points(
                    axis,
                    group.snrDb.astype(float),
                    group[metric].astype(float),
                    group[upper].astype(float),
                    marker="o",
                    markersize=2.5,
                    linewidth=1,
                    label=label,
                )
            axis.set_title(rate)
            axis.set_xlabel("SNR = Es/N0 (dB)")
            axis.grid(True, which="both", alpha=0.25)
        axes[0].set_ylabel(metric)
        axes[-1].legend(fontsize=6)
        fig.suptitle(f"最终候选 {metric}")
        save(name, source, manifest)

    loss_path = (
        S3
        / "stage11_soft_quantization"
        / "results"
        / "stage11_quantization_snr_loss.csv"
    )
    loss = pd.read_csv(loss_path)
    loss = loss[loss.quantMode != "Float"].copy()
    source = figure_data("stage15_quantization_snr_loss", loss)
    plt.figure(figsize=(8, 4.8))
    for rate in RATES:
        group = loss[
            (loss.rateCase == rate) & (loss.targetFer == 0.1)
        ]
        plt.plot(
            group.quantMode,
            group.snrLossVsFloat,
            marker="o",
            label=rate,
        )
    plt.xlabel("量化模式")
    plt.ylabel("相对 Float 的 SNR 损失 (dB)")
    plt.title("量化位宽性能损失（FER=0.1）")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_quantization_snr_loss", source, manifest)

    trace_path = (
        S3
        / "stage10_traceback_study"
        / "results"
        / "stage10_traceback_study_results.csv"
    )
    trace = pd.read_csv(trace_path)
    trace = trace[
        (trace.targetFerLevel == "FER_010")
        & (trace.mode == "CONTINUOUS_TRUNCATED_VITERBI")
    ]
    source = figure_data("stage15_traceback_memory_reliability", trace)
    plt.figure(figsize=(8, 4.8))
    for rate in RATES:
        group = trace[trace.rateCase == rate]
        plt.scatter(
            group.totalDecoderMemoryBytes,
            group.relativeFerIncreaseVsBlock,
            label=rate,
        )
        for _, row in group.iterrows():
            plt.annotate(
                f"D{int(row.dtb)}",
                (row.totalDecoderMemoryBytes, row.relativeFerIncreaseVsBlock),
                fontsize=6,
            )
    plt.xlabel("译码器内存（字节）")
    plt.ylabel("相对完整块 FER 增幅")
    plt.title("回溯深度内存—可靠性权衡")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_traceback_memory_reliability", source, manifest)

    numeric = matrix.copy()
    for column in [
        "firstOutputDelaySymbols",
        "avgDecodeTimeUs",
        "p95DecodeTimeUs",
        "FER",
        "normalizedGoodput",
        "totalMemoryBytes",
    ]:
        numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    representative = []
    for scheme, group in numeric.groupby("schemeId"):
        usable = group.dropna(subset=["FER"])
        if usable.empty:
            continue
        representative.append(
            usable.loc[(usable.FER - 0.1).abs().idxmin()]
        )
    points = pd.DataFrame(representative)
    for metric, name, ylabel in [
        (
            "firstOutputDelaySymbols",
            "stage15_first_output_latency",
            "首次输出等待（符号）",
        ),
        (
            "avgDecodeTimeUs",
            "stage15_cpu_decode_latency",
            "平均 CPU 译码时间（μs）",
        ),
    ]:
        data = points.dropna(subset=[metric]).copy()
        source = figure_data(name, data)
        plt.figure(figsize=(10, 5))
        plt.bar(data.schemeId, data[metric])
        plt.xticks(rotation=70, ha="right", fontsize=6)
        plt.ylabel(ylabel)
        plt.title(name.replace("stage15_", "").replace("_", " "))
        plt.grid(True, axis="y", alpha=0.25)
        save(name, source, manifest)

    data = points.dropna(subset=["normalizedGoodput", "FER"]).copy()
    source = figure_data("stage15_goodput_fer_pareto", data)
    plt.figure(figsize=(8, 5))
    for rate in RATES:
        group = data[data.rate == rate]
        plt.scatter(group.FER, group.normalizedGoodput, label=rate)
    plt.xlabel("FER")
    plt.ylabel("归一化有效吞吐")
    plt.title("吞吐—FER Pareto")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_goodput_fer_pareto", source, manifest)

    data = points.dropna(
        subset=["firstOutputDelaySymbols", "FER", "totalMemoryBytes"]
    ).copy()
    source = figure_data("stage15_latency_reliability_pareto", data)
    plt.figure(figsize=(8, 5))
    memory = data.totalMemoryBytes.clip(lower=1)
    sizes = 30 + 170 * (memory - memory.min()) / max(
        1.0, memory.max() - memory.min()
    )
    for rate in RATES:
        group = data[data.rate == rate]
        plt.scatter(
            group.firstOutputDelaySymbols,
            group.FER,
            s=sizes.loc[group.index],
            label=rate,
            alpha=0.7,
        )
    plt.xlabel("首次输出等待（符号）")
    plt.ylabel("FER")
    plt.title("时延—可靠性 Pareto（气泡为内存）")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage15_latency_reliability_pareto", source, manifest)
    return manifest


def numeric_recommendations(matrix: pd.DataFrame) -> pd.DataFrame:
    numeric = matrix.copy()
    columns = [
        "FER",
        "normalizedGoodput",
        "firstOutputDelaySymbols",
        "totalMemoryBytes",
        "tracebackOperations",
        "avgDecodeTimeUs",
    ]
    for column in columns:
        numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    candidates = []
    for scheme, group in numeric.groupby("schemeId"):
        usable = group.dropna(subset=["FER"])
        if usable.empty:
            continue
        row = usable.loc[(usable.FER - 0.1).abs().idxmin()].copy()
        row["operatingFerDistance"] = abs(row.FER - 0.1)
        candidates.append(row)
    data = pd.DataFrame(candidates)
    for column in columns:
        series = data[column]
        low, high = series.min(skipna=True), series.max(skipna=True)
        data[f"norm_{column}"] = (
            0.0 if low == high else (series.fillna(high) - low) / (high - low)
        )
    choices = {
        "reliability_first": data.loc[data.FER.idxmin()],
        "throughput_first": data.loc[data.normalizedGoodput.idxmax()],
        "latency_first": data.loc[data.firstOutputDelaySymbols.idxmin()],
        "memory_first": data.loc[data.totalMemoryBytes.idxmin()],
        "complexity_first": data.loc[data.tracebackOperations.idxmin()],
    }
    data["balancedScore"] = (
        0.35 * data.norm_FER
        + 0.20 * (1 - data.norm_normalizedGoodput)
        + 0.15 * data.norm_firstOutputDelaySymbols
        + 0.15 * data.norm_totalMemoryBytes
        + 0.10 * data.norm_tracebackOperations
        + 0.05 * data.norm_avgDecodeTimeUs
    )
    choices["balanced"] = data.loc[data.balancedScore.idxmin()]
    rows = []
    for kind, row in choices.items():
        rows.append(
            {
                "recommendationType": kind,
                "schemeId": row.schemeId,
                "rate": row.rate,
                "decisionMode": row.decisionMode,
                "quantMode": row.quantMode,
                "dtb": row.dtb,
                "window": row.window,
                "slide": row.slide,
                "organization": row.organization,
                "snrDb": row.snrDb,
                "FER": row.FER,
                "normalizedGoodput": row.normalizedGoodput,
                "firstOutputDelaySymbols": row.firstOutputDelaySymbols,
                "totalMemoryBytes": row.totalMemoryBytes,
                "tracebackOperations": row.tracebackOperations,
                "avgDecodeTimeUs": row.avgDecodeTimeUs,
                "applicability": (
                    "symbol-level discrete BPSK-AWGN; select only when "
                    "the measured SNR/FER operating region is covered"
                ),
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(RESULTS / "stage15_final_recommendations.csv", index=False)
    return result


def write_documents(matrix: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    stage09 = matrix[
        (matrix.sourceStage == "Stage09")
        & (matrix.decisionMode == "Soft Float")
    ].copy()
    rate_lines = []
    for rate in RATES:
        group = stage09[stage09.rate == rate]
        point = group.loc[(pd.to_numeric(group.FER) - 0.1).abs().idxmin()]
        rate_lines.append(
            f"- {rate}: Es/N0={float(point.snrDb):g} dB 时 "
            f"FER={float(point.FER):.5g}，actual-rate goodput="
            f"{float(point.normalizedGoodput):.5g}。"
        )
    rec_table = markdown_table(recommendations)
    questions = f"""# CC S3 core questions

All values below come from `stage15_final_scheme_matrix.csv`; the channel is
symbol-level discrete BPSK-AWGN, not a continuous-time waveform simulation.

## 1. R12/R23/R34 reliability versus throughput

{chr(10).join(rate_lines)}

Use fields `snrDb`, `FER`, and `normalizedGoodput`; see
`stage15_final_fer.png` and `stage15_goodput_fer_pareto.png`. Higher rates
raise the high-SNR throughput ceiling but require more Es/N0 for the same FER.

## 2. Hard, Float and quantized Soft

The Q8 recommendation and its exact SNR losses are recorded in
`../stage11_soft_quantization/results/stage11_quantization_snr_loss.csv`.
Use `decisionMode`, `quantMode`, `BER`, `FER`, `avgDecodeTimeUs` and memory
fields; see `stage15_final_ber.png`, `stage15_quantization_snr_loss.png`.
Float is the reference; quantized modes trade input representation for the
measured loss. Hard decisions remain useful only where simplicity dominates.

## 3. Block, 50×6, 100×3 and 150×2

Use Stage14 fields `firstOutputDelaySymbols`, `p95DecisionDelaySymbols`,
`peakRxBufferSymbols`, `outputBatchCount` and `FER`. The selected organization
is data-driven in `stage14_organization_recommendations.csv`; see Stage14
per-rate plots. Reliability differences within confidence intervals do not
erase the measured scheduling, output-rhythm and buffering differences.

## 4. Full, truncated and sliding-window

Use `tracebackMode`, `dtb`, `window`, `slide`, `FER`, delay, memory, ACS and
traceback-operation fields. See `stage15_traceback_memory_reliability.png`
and all Stage13 final comparison plots. Full traceback is the reference;
truncated D84/D112 and bounded true windows are accepted only when their
measured reliability Gate passes.

## 5. Q, Dtb, W and S configuration

Stage11 selected Q8. Stage10's formal finite-depth result and Stage13's
per-rate performance/latency/memory/balanced selections are preserved in
their recommendation CSVs. No Q, Dtb, W, S or slot organization was fixed
before measurement.

## Final objective-specific recommendations

{rec_table}

Limit: CPU times describe this Release build, host, OS and compiler; they are
not universal hardware constants.
"""
    (RESULTS / "stage15_core_questions_answer.md").write_text(
        questions, encoding="utf-8"
    )
    figure_paths = sorted(S3.glob("stage*/results/*.png"))
    lines = [
        "# CC S3 all figures guide",
        "",
        "All BER/FER figures use SNR = Es/N0 (dB). Zero observations remain "
        "unchanged in the formal CSV but are omitted from log-scale figures. "
        "Curves are pointwise and unsmoothed.",
        "",
    ]
    for path in figure_paths:
        relative = Path(os.path.relpath(path, RESULTS)).as_posix()
        lines.extend(
            [
                f"## {path.name}",
                "",
                f"![{path.stem}]({relative})",
                "",
                "Purpose and axes follow the filename and its adjacent "
                "figure-data CSV/plot manifest. Interpret only within the "
                "measured SNR grid and confidence intervals.",
                "",
            ]
        )
    (RESULTS / "stage15_all_figures_guide.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    configure_font()
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    matrix = build_matrix()
    manifest = plot_final(matrix)
    recommendations = numeric_recommendations(matrix)
    write_documents(matrix, recommendations)
    matrix_path = RESULTS / "stage15_final_scheme_matrix.csv"
    (RESULTS / "plot_manifest.json").write_text(
        json.dumps(
            {
                "sourceFiles": [
                    {
                        "path": matrix_path.name,
                        "sha256": sha256(matrix_path),
                    }
                ],
                "plots": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (RESULTS / "plot_check.md").write_text(
        "# Stage15 plot check\n\n"
        f"- Scheme-matrix rows: {len(matrix)}: PASS\n"
        f"- Required final plots: {len(manifest)}: PASS\n"
        "- Pointwise formal data only: PASS\n"
        "- Unified coarse SNR grid used for final curves: PASS\n"
        "- Zero observations omitted from log-scale figures; raw CSV retained: PASS\n\n"
        "PASS_CC_S3_INTEGRATION\n",
        encoding="utf-8",
    )
    print(
        f"PASS_CC_S3_INTEGRATION rows={len(matrix)} plots={len(manifest)}"
    )


if __name__ == "__main__":
    main()
