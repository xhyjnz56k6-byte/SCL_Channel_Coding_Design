#!/usr/bin/env python3
"""Finalize Stage13 dense data, reference comparisons and research plots."""

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
DENSE_RUNTIME = STAGE / "runtime" / "revision_20260729_formal_dense"
REFERENCE_RUNTIME = STAGE / "runtime" / "revision_20260729_reference"
STAGE10_RESULTS = (
    STAGE.parent / "stage10_traceback_study" / "results"
)
D84_RUNTIME = STAGE / "runtime" / "revision_20260729_d84_revalidation"
D84_REFERENCE_RUNTIME = (
    STAGE / "runtime" / "revision_20260729_d84_reference"
)
RATES = ["R12", "R23", "R34"]
RECOMMENDATION_TYPES = [
    "performance_first",
    "balanced",
    "latency_first",
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


def load_dense() -> pd.DataFrame:
    plan = pd.read_csv(RESULTS / "stage13_formal_dense_plan.csv")
    paths = sorted(DENSE_RUNTIME.glob("stage13_result_shard_*.csv"))
    if len(paths) != 4:
        raise RuntimeError(f"expected four dense shards, found {len(paths)}")
    dense = pd.concat((pd.read_csv(path) for path in paths), ignore_index=True)
    if len(dense) != len(plan):
        raise RuntimeError(
            f"dense plan/result mismatch: {len(plan)} vs {len(dense)}"
        )
    expected = set(
        zip(
            plan.rateCase,
            plan.candidateId,
            plan.snrDb.round(10),
        )
    )
    observed = set(
        zip(
            dense.rateCase,
            dense.candidateId,
            dense.snrDb.round(10),
        )
    )
    if expected != observed:
        raise RuntimeError("dense key mismatch")
    dense.to_csv(RESULTS / "stage13_formal_dense_results.csv", index=False)
    return dense


def load_reference() -> pd.DataFrame:
    paths = sorted(REFERENCE_RUNTIME.glob("stage13_reference_shard_*.csv"))
    if len(paths) != 4:
        raise RuntimeError(f"expected four reference shards, found {len(paths)}")
    reference = pd.concat(
        (pd.read_csv(path) for path in paths), ignore_index=True
    )
    if len(reference) != 3 * 31 * 3:
        raise RuntimeError(
            f"expected 279 Stage13 reference rows, found {len(reference)}"
        )
    keys = reference[
        ["rateCase", "snrDb", "tracebackMode"]
    ].drop_duplicates()
    if len(keys) != len(reference):
        raise RuntimeError("duplicate Stage13 reference keys")
    reference.to_csv(
        RESULTS / "stage13_reference_comparison.csv", index=False
    )
    return reference


def load_d84_revalidation() -> tuple[pd.DataFrame, str]:
    candidate_paths = sorted(
        D84_RUNTIME.glob("stage13_result_shard_*.csv")
    )
    reference_paths = sorted(
        D84_REFERENCE_RUNTIME.glob("stage13_reference_shard_*.csv")
    )
    if len(candidate_paths) != 4 or len(reference_paths) != 4:
        raise RuntimeError("D84 candidate/reference shards incomplete")
    candidates = pd.concat(
        (pd.read_csv(path) for path in candidate_paths), ignore_index=True
    )
    references = pd.concat(
        (pd.read_csv(path) for path in reference_paths), ignore_index=True
    )
    if len(candidates) != 18 or len(references) != 27:
        raise RuntimeError(
            f"D84 revalidation row mismatch: {len(candidates)}/{len(references)}"
        )
    candidates["comparisonMode"] = candidates.candidateId.map(
        lambda item: (
            "TRUE_SLIDING_WINDOW_D84"
            if "TRUE-D84" in item
            else "TRUE_SLIDING_WINDOW_BALANCED"
        )
    )
    references["comparisonMode"] = references.tracebackMode
    combined = pd.concat([references, candidates], ignore_index=True)
    table_rows = []
    d84_pass = True
    for rate in RATES:
        block = references[
            (references.rateCase == rate)
            & (references.tracebackMode == "BLOCK_FULL_TRACEBACK")
        ].set_index("snrDb")
        for mode in [
            "CONTINUOUS_TRUNCATED_D84",
            "TRUE_SLIDING_WINDOW_D84",
            "TRUE_SLIDING_WINDOW_BALANCED",
        ]:
            source = combined[
                (combined.rateCase == rate)
                & (combined.comparisonMode == mode)
            ].set_index("snrDb")
            relative = (source.FER - block.FER) / block.FER
            worst = float(relative.max())
            timing_column = (
                "avgDecodeTimeUs"
                if mode == "CONTINUOUS_TRUNCATED_D84"
                else "avgWindowProcessingTimeUs"
            )
            if mode == "TRUE_SLIDING_WINDOW_D84":
                d84_pass = d84_pass and worst <= 0.05
            table_rows.append(
                {
                    "rateCase": rate,
                    "mode": mode,
                    "worstRelativeFerIncreaseVsBlock": worst,
                    "maxMismatchFramesVsBlock": int(
                        source.mismatchVsBlockFrames.max()
                    ),
                    "meanDecodeTimeUs": float(
                        source[timing_column].mean()
                    ),
                    "maxTotalMemoryBytes": int(
                        source.totalMemoryBytes.max()
                    ),
                    "meanTracebackOperationsPerFrame": float(
                        (source.tracebackOperations / source.frames).mean()
                    ),
                }
            )
    summary = pd.DataFrame(table_rows)
    summary.to_csv(
        RESULTS / "stage10_d84_window_revalidation_summary.csv",
        index=False,
    )
    conclusion = (
        "D84 remains eligible under the true-window 5% FER gate."
        if d84_pass
        else "D84 is revoked as a final true-window recommendation because "
        "at least one rate exceeds the 5% FER gate."
    )
    text = (
        "# D84 true-window revalidation\n\n"
        "All four modes use the same payload, encoded stream, puncturing, "
        "Gaussian mother noise, SNR, frame indices and stop rule at each "
        "rate/FER-level scenario.\n\n"
        + markdown_table(summary)
        + "\n\n"
        + conclusion
        + "\n"
    )
    return combined, text


def build_comparison(
    coarse: pd.DataFrame,
    reference: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in reference.iterrows():
        rows.append(
            {
                **row.to_dict(),
                "comparisonMode": row.tracebackMode,
                "windowBits": 306 if row.tracebackMode == "BLOCK_FULL_TRACEBACK" else 0,
                "slideBits": 300,
            }
        )
    for rate in RATES:
        for kind in RECOMMENDATION_TYPES:
            rec = recommendations[
                (recommendations.rateCase == rate)
                & (recommendations.recommendationType == kind)
            ]
            if len(rec) != 1:
                raise RuntimeError(f"missing recommendation {rate}/{kind}")
            candidate = rec.iloc[0].candidateId
            curve = coarse[
                (coarse.rateCase == rate) & (coarse.candidateId == candidate)
            ]
            if len(curve) != 31:
                raise RuntimeError(f"incomplete sliding curve {rate}/{candidate}")
            for _, row in curve.iterrows():
                item = row.to_dict()
                item.update(
                    {
                        "comparisonMode": f"SLIDING_{kind.upper()}",
                        "tracebackMode": "TRUE_SLIDING_WINDOW",
                        "dtb": row.dtb,
                        "avgDecodeTimeUs": row.avgWindowProcessingTimeUs,
                        "p95DecodeTimeUs": row.p95WindowProcessingTimeUs,
                    }
                )
                rows.append(item)
    result = pd.DataFrame(rows)
    result.to_csv(RESULTS / "stage13_final_comparison.csv", index=False)
    return result


def control_plots(
    prescan: pd.DataFrame, summary: pd.DataFrame, manifest: list[dict]
) -> None:
    controls = [
        ("A_CHANGE_W", "windowBits", "W", "w"),
        ("B_CHANGE_S", "slideBits", "S", "s"),
        ("C_CHANGE_D", "dtb", "D", "d"),
    ]
    for experiment, xfield, label, short in controls:
        data = prescan[
            (prescan.experimentId == experiment)
            & (prescan.targetFerLevel == "FER_010")
        ].copy()
        source = figure_data(f"stage13_control_{short}_ber_fer", data)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        for rate in RATES:
            group = data[data.rateCase == rate].sort_values(xfield)
            semilogy_points(
                axes[0],
                group[xfield],
                group.BER,
                group.berCiHigh,
                marker="o",
                label=rate,
            )
            semilogy_points(
                axes[1],
                group[xfield],
                group.FER,
                group.ferCiHigh,
                marker="o",
                label=rate,
            )
        for axis, metric in zip(axes, ["BER", "FER"]):
            axis.set_xlabel(label)
            axis.set_ylabel(metric)
            axis.grid(True, which="both", alpha=0.25)
            axis.legend()
        fig.suptitle(f"固定其余参数时 {label} 对可靠性的影响")
        save(f"stage13_control_{short}_ber_fer", source, manifest)

    w = prescan[
        (prescan.experimentId == "A_CHANGE_W")
        & (prescan.targetFerLevel == "FER_010")
    ].copy()
    for metric, name, ylabel in [
        ("firstOutputDelaySymbols", "stage13_w_first_output_delay", "符号"),
        ("totalMemoryBytes", "stage13_w_actual_memory", "字节"),
    ]:
        source = figure_data(name, w)
        plt.figure(figsize=(7.2, 4.8))
        for rate in RATES:
            group = w[w.rateCase == rate].sort_values("windowBits")
            plt.plot(group.windowBits, group[metric], marker="o", label=rate)
        plt.xlabel("W")
        plt.ylabel(ylabel)
        plt.title("W 与" + ("首次输出等待" if "first" in name else "实际内存"))
        plt.grid(True, alpha=0.25)
        plt.legend()
        save(name, source, manifest)

    s = prescan[
        (prescan.experimentId == "B_CHANGE_S")
        & (prescan.targetFerLevel == "FER_010")
    ].copy()
    source = figure_data("stage13_s_steady_output_interval", s)
    plt.figure(figsize=(7.2, 4.8))
    for rate in RATES:
        group = s[s.rateCase == rate].sort_values("slideBits")
        plt.plot(
            group.slideBits,
            group.steadyOutputIntervalMean,
            marker="o",
            label=rate,
        )
    plt.xlabel("S")
    plt.ylabel("稳态输出间隔（符号）")
    plt.title("S 与稳态输出节奏")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage13_s_steady_output_interval", source, manifest)

    d = prescan[
        (prescan.experimentId == "C_CHANGE_D")
        & (prescan.targetFerLevel == "FER_010")
    ].copy()
    d["tracebackPerFrame"] = d.tracebackOperations / d.frames
    source = figure_data("stage13_d_traceback_operations", d)
    plt.figure(figsize=(7.2, 4.8))
    for rate in RATES:
        group = d[d.rateCase == rate].sort_values("dtb")
        plt.plot(group.dtb, group.tracebackPerFrame, marker="o", label=rate)
    plt.xlabel("D")
    plt.ylabel("回溯操作/帧")
    plt.title("D 与回溯操作数")
    plt.grid(True, alpha=0.25)
    plt.legend()
    save("stage13_d_traceback_operations", source, manifest)

    heat = prescan[prescan.targetFerLevel == "FER_010"].copy()
    pivot = heat.pivot_table(
        index="windowBits",
        columns="slideBits",
        values="mismatchVsBlockFrames",
        aggfunc="mean",
    )
    source = figure_data("stage13_mismatch_heatmap", heat)
    plt.figure(figsize=(7.2, 4.8))
    image = plt.imshow(
        pivot.fillna(np.nan).values,
        aspect="auto",
        origin="lower",
        cmap="viridis",
    )
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("S")
    plt.ylabel("W")
    plt.title("与完整块译码不一致帧数")
    plt.colorbar(image, label="平均 mismatch 帧数")
    save("stage13_mismatch_heatmap", source, manifest)

    for x, name, xlabel in [
        (
            "meanP95DecisionDelaySymbols",
            "stage13_delay_reliability_pareto",
            "P95 决策等待（符号）",
        ),
        (
            "totalMemoryBytes",
            "stage13_memory_reliability_pareto",
            "总内存（字节）",
        ),
    ]:
        source = figure_data(name, summary)
        plt.figure(figsize=(7.2, 4.8))
        for rate in RATES:
            group = summary[summary.rateCase == rate]
            plt.scatter(
                group[x],
                group.worstCoveredSnrLoss,
                label=rate,
                alpha=0.8,
            )
        plt.xlabel(xlabel)
        plt.ylabel("最坏目标 FER SNR 损失 (dB)")
        plt.title("滑窗参数 Pareto 权衡")
        plt.grid(True, alpha=0.25)
        plt.legend()
        save(name, source, manifest)


def final_plots(comparison: pd.DataFrame, manifest: list[dict]) -> None:
    mode_order = [
        "BLOCK_FULL_TRACEBACK",
        "CONTINUOUS_TRUNCATED_D84",
        "SLIDING_PERFORMANCE_FIRST",
        "SLIDING_BALANCED",
        "SLIDING_LATENCY_FIRST",
    ]
    labels = {
        "BLOCK_FULL_TRACEBACK": "Block full",
        "CONTINUOUS_TRUNCATED_D84": "Truncated D84",
        "SLIDING_PERFORMANCE_FIRST": "Sliding performance",
        "SLIDING_BALANCED": "Sliding balanced",
        "SLIDING_LATENCY_FIRST": "Sliding latency",
    }
    for metric, upper, name, ylabel in [
        ("BER", "berCiHigh", "stage13_final_ber_comparison", "BER"),
        ("FER", "ferCiHigh", "stage13_final_fer_comparison", "FER"),
    ]:
        source = figure_data(name, comparison)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
        for axis, rate in zip(axes, RATES):
            rate_rows = comparison[comparison.rateCase == rate]
            for mode in mode_order:
                group = rate_rows[
                    rate_rows.comparisonMode == mode
                ].sort_values("snrDb")
                semilogy_points(
                    axis,
                    group.snrDb,
                    group[metric],
                    group[upper],
                    marker="o",
                    markersize=2.5,
                    linewidth=1,
                    label=labels[mode],
                )
            axis.set_title(rate)
            axis.set_xlabel("SNR = Es/N0 (dB)")
            axis.grid(True, which="both", alpha=0.25)
        axes[0].set_ylabel(ylabel)
        axes[-1].legend(fontsize=8)
        fig.suptitle(f"完整块、截断与真滑窗 {ylabel} 对比")
        save(name, source, manifest)

    representative = []
    for rate in RATES:
        block = comparison[
            (comparison.rateCase == rate)
            & (comparison.comparisonMode == "BLOCK_FULL_TRACEBACK")
        ]
        snr = float(block.loc[(block.FER - 0.1).abs().idxmin(), "snrDb"])
        representative.append(
            comparison[
                (comparison.rateCase == rate)
                & (comparison.snrDb == snr)
                & (comparison.comparisonMode.isin(mode_order))
            ]
        )
    points = pd.concat(representative, ignore_index=True)
    for metrics, name, ylabel in [
        (
            [
                "firstOutputDelaySymbols",
                "avgDecisionDelaySymbols",
                "p95DecisionDelaySymbols",
            ],
            "stage13_final_latency_comparison",
            "符号",
        ),
        (
            ["totalMemoryBytes"],
            "stage13_final_memory_comparison",
            "字节",
        ),
        (
            ["ACSCount", "tracebackOperations"],
            "stage13_final_complexity_comparison",
            "操作数",
        ),
    ]:
        source = figure_data(name, points)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
        for axis, rate in zip(axes, RATES):
            group = points[points.rateCase == rate]
            x = np.arange(len(group))
            width = 0.8 / len(metrics)
            for index, metric in enumerate(metrics):
                axis.bar(
                    x + (index - (len(metrics) - 1) / 2) * width,
                    group[metric],
                    width,
                    label=metric,
                )
            axis.set_xticks(x)
            axis.set_xticklabels(
                [labels.get(mode, mode) for mode in group.comparisonMode],
                rotation=35,
                ha="right",
                fontsize=7,
            )
            axis.set_title(rate)
            axis.grid(True, axis="y", alpha=0.25)
        axes[0].set_ylabel(ylabel)
        axes[-1].legend(fontsize=7)
        fig.suptitle(name.replace("stage13_final_", "").replace("_", " "))
        save(name, source, manifest)


def main() -> None:
    configure_font()
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    dense = load_dense()
    coarse = pd.read_csv(RESULTS / "stage13_formal_coarse_results.csv")
    reference = load_reference()
    recommendations = pd.read_csv(
        RESULTS / "stage13_final_recommendations.csv"
    )
    prescan = pd.concat(
        [
            pd.read_csv(RESULTS / "stage13_controlled_prescan_results.csv"),
            pd.read_csv(RESULTS / "stage13_r34_supplement_results.csv"),
        ],
        ignore_index=True,
    )
    summary = pd.read_csv(RESULTS / "stage13_formal_candidate_summary.csv")
    comparison = build_comparison(coarse, reference, recommendations)
    manifest: list[dict] = []
    control_plots(prescan, summary, manifest)
    final_plots(comparison, manifest)
    sources = [
        RESULTS / "stage13_formal_coarse_results.csv",
        RESULTS / "stage13_formal_dense_results.csv",
        RESULTS / "stage13_reference_comparison.csv",
        RESULTS / "stage13_final_comparison.csv",
    ]
    (RESULTS / "plot_manifest.json").write_text(
        json.dumps(
            {
                "sourceFiles": [
                    {
                        "path": path.name,
                        "sha256": sha256(path),
                    }
                    for path in sources
                ],
                "plots": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    revalidation, revalidation_text = load_d84_revalidation()
    revalidation.to_csv(
        RESULTS / "stage10_d84_window_revalidation.csv", index=False
    )
    STAGE10_RESULTS.mkdir(parents=True, exist_ok=True)
    revalidation.to_csv(
        STAGE10_RESULTS / "stage10_d84_window_revalidation.csv",
        index=False,
    )
    (RESULTS / "stage10_d84_window_revalidation.md").write_text(
        revalidation_text, encoding="utf-8"
    )
    (
        STAGE10_RESULTS / "stage10_d84_window_revalidation.md"
    ).write_text(revalidation_text, encoding="utf-8")
    (RESULTS / "plot_check.md").write_text(
        "# Stage13 plot check\n\n"
        f"- Dense rows: {len(dense)}: PASS\n"
        f"- Final comparison rows: {len(comparison)}: PASS\n"
        f"- Plot count: {len(manifest)}: PASS\n"
        "- Pointwise CSV plotting without smoothing: PASS\n"
        "- Zero BER/FER observations omitted from log-scale figures; raw CSV retained: PASS\n\n"
        "PASS_STAGE13_FINAL_COMPARISON\n",
        encoding="utf-8",
    )
    print(
        "PASS_STAGE13_FINAL_COMPARISON "
        f"denseRows={len(dense)} comparisonRows={len(comparison)} "
        f"plots={len(manifest)}"
    )


if __name__ == "__main__":
    main()
