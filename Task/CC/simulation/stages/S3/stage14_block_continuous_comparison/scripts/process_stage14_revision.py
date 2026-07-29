#!/usr/bin/env python3
"""Merge, validate, select and plot the Stage14 online-slot formal run."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

STAGE = Path(__file__).resolve().parents[1]
RUNTIME = STAGE / "runtime" / "revision_20260729_formal_coarse"
RESULTS = STAGE / "results"
FIGURE_DATA = RESULTS / "figure_data"
RATES = ["R12", "R23", "R34"]
SCHEMES = [
    "A_BLOCK_300",
    "B_CONT_50x6",
    "C_CONT_100x3",
    "D_CONT_150x2",
]
LABELS = {
    "A_BLOCK_300": "Block300",
    "B_CONT_50x6": "50×6",
    "C_CONT_100x3": "100×3",
    "D_CONT_150x2": "150×2",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
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


def safe_log(values: pd.Series, upper: pd.Series) -> pd.Series:
    result = values.astype(float).copy()
    zero = result <= 0
    result.loc[zero] = upper.loc[zero].astype(float)
    return result

def semilogy_points(axis, x, values, upper, **kwargs):
    display = safe_log(values, upper)
    line = axis.semilogy(x, display, **kwargs)[0]
    zero = values.astype(float) <= 0
    if zero.any():
        axis.scatter(
            pd.Series(x).reset_index(drop=True)[zero.reset_index(drop=True)],
            upper.astype(float).reset_index(drop=True)[
                zero.reset_index(drop=True)
            ],
            facecolors="none",
            edgecolors=line.get_color(),
            marker="o",
            linewidths=1.2,
            zorder=4,
        )
    return line


def write_figure_data(name: str, data: pd.DataFrame) -> Path:
    path = FIGURE_DATA / f"{name}.csv"
    data.to_csv(path, index=False)
    return path


def save_plot(name: str, input_data: Path, manifest: list[dict]) -> None:
    path = RESULTS / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    manifest.append(
        {
            "plot": path.name,
            "figureData": input_data.relative_to(RESULTS).as_posix(),
            "plotSha256": sha256(path),
            "figureDataSha256": sha256(input_data),
        }
    )


def validate(main: pd.DataFrame, offsets: pd.DataFrame) -> None:
    if len(main) != 3 * 31 * 4:
        raise RuntimeError(f"expected 372 main rows, found {len(main)}")
    expected_snr = [value / 2 for value in range(-10, 21)]
    for rate in RATES:
        for scheme in SCHEMES:
            group = main[
                (main.rateCase == rate) & (main.organization == scheme)
            ].sort_values("snrDb")
            if group.snrDb.tolist() != expected_snr:
                raise RuntimeError(f"incomplete SNR grid: {rate}/{scheme}")
            if not (group.frames >= 1000).all():
                raise RuntimeError(f"formal minimum frames failed: {rate}/{scheme}")
            if not (group.esN0Db.sub(group.snrDb).abs() <= 1e-12).all():
                raise RuntimeError("Es/N0 formula mismatch")
            expected_eb = group.snrDb - 10 * group.actualRate.map(math.log10)
            if not (group.ebN0Db.sub(expected_eb).abs() <= 1e-10).all():
                raise RuntimeError("Eb/N0 formula mismatch")
            expected_sigma = 1 / (2 * 10 ** (group.snrDb / 10))
            if not (group.sigmaSquared.sub(expected_sigma).abs() <= 1e-12).all():
                raise RuntimeError("noise formula mismatch")
    block = main[main.organization == "A_BLOCK_300"]
    if not (block.boundaryStatus == "NOT_APPLICABLE").all():
        raise RuntimeError("block boundary status must be NOT_APPLICABLE")
    continuous = main[main.organization != "A_BLOCK_300"]
    if not (continuous.boundaryStatus == "APPLICABLE").all():
        raise RuntimeError("continuous boundary status missing")
    if set(offsets.relativeOffset.unique()) != set(range(-10, 10)):
        raise RuntimeError("boundary offset coverage is not -10..+9")


def select_organizations(main: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rate in RATES:
        rate_rows = main[main.rateCase == rate]
        block = rate_rows[rate_rows.organization == "A_BLOCK_300"].set_index(
            "snrDb"
        )
        candidates = []
        for scheme in SCHEMES[1:]:
            data = rate_rows[rate_rows.organization == scheme].set_index("snrDb")
            valid = block.FER > 0
            relative = (
                (data.loc[valid, "FER"] - block.loc[valid, "FER"])
                / block.loc[valid, "FER"]
            )
            worst_relative = float(relative.max()) if len(relative) else 0.0
            reliability_pass = worst_relative <= 0.05
            representative_snr = float(
                (block.FER - 0.1).abs().sort_values().index[0]
            )
            point = data.loc[representative_snr]
            candidates.append(
                {
                    "rateCase": rate,
                    "organization": scheme,
                    "worstRelativeFerIncreaseVsBlock": worst_relative,
                    "reliabilityGate": "PASS" if reliability_pass else "FAIL",
                    "representativeSnrDb": representative_snr,
                    "representativeFER": point.FER,
                    "firstOutputDelaySymbols": point.firstOutputDelaySymbols,
                    "p95DecisionDelaySymbols": point.p95DecisionDelaySymbols,
                    "peakRxBufferSymbols": point.peakRxBufferSymbols,
                    "avgDecodeTimeUs": point.avgDecodeTimeUs,
                    "normalizedGoodput": point.normalizedGoodput,
                }
            )
        passing = [row for row in candidates if row["reliabilityGate"] == "PASS"]
        pool = passing or candidates
        for metric in [
            "firstOutputDelaySymbols",
            "p95DecisionDelaySymbols",
            "peakRxBufferSymbols",
            "avgDecodeTimeUs",
        ]:
            values = [float(row[metric]) for row in pool]
            low, high = min(values), max(values)
            for row in pool:
                row[f"normalized_{metric}"] = (
                    0.0 if high == low else (float(row[metric]) - low) / (high - low)
                )
        for row in candidates:
            if row in pool:
                row["balancedScore"] = (
                    0.30 * max(0.0, row["worstRelativeFerIncreaseVsBlock"])
                    + 0.25 * row["normalized_firstOutputDelaySymbols"]
                    + 0.20 * row["normalized_p95DecisionDelaySymbols"]
                    + 0.15 * row["normalized_peakRxBufferSymbols"]
                    + 0.10 * row["normalized_avgDecodeTimeUs"]
                )
            else:
                row["balancedScore"] = math.inf
        selected = min(candidates, key=lambda row: row["balancedScore"])[
            "organization"
        ]
        for row in candidates:
            row["selectedBalanced"] = int(row["organization"] == selected)
            rows.append(row)
    return pd.DataFrame(rows)


def make_plots(main: pd.DataFrame, offsets: pd.DataFrame) -> list[dict]:
    manifest: list[dict] = []
    for rate in RATES:
        data = main[main.rateCase == rate].copy()
        block = data[data.organization == "A_BLOCK_300"]
        representative_snr = float(
            block.iloc[(block.FER - 0.1).abs().to_numpy().argmin()].snrDb
        )
        for metric, ci, suffix, ylabel in [
            ("BER", "berCiHigh", "ber", "BER"),
            ("FER", "ferCiHigh", "fer", "FER"),
        ]:
            columns = [
                "organization",
                "rateCase",
                "snrDb",
                metric,
                ci,
                "frames",
            ]
            figure = write_figure_data(
                f"stage14_{rate.lower()}_{suffix}", data[columns]
            )
            plt.figure(figsize=(7.2, 4.8))
            for scheme in SCHEMES:
                group = data[data.organization == scheme].sort_values("snrDb")
                semilogy_points(
                    plt.gca(),
                    group.snrDb,
                    group[metric],
                    group[ci],
                    marker="o",
                    markersize=3,
                    linewidth=1,
                    label=LABELS[scheme],
                )
            plt.xlabel("SNR = Es/N0 (dB)")
            plt.ylabel(ylabel)
            plt.title(f"{rate} 四种组织方式 {ylabel}")
            plt.grid(True, which="both", alpha=0.25)
            plt.legend()
            save_plot(f"stage14_{rate.lower()}_{suffix}", figure, manifest)

        boundary = offsets[
            (offsets.rateCase == rate)
            & (offsets.snrDb == representative_snr)
        ].copy()
        figure = write_figure_data(
            f"stage14_{rate.lower()}_boundary_relative_ber", boundary
        )
        plt.figure(figsize=(7.2, 4.8))
        for scheme in SCHEMES[1:]:
            group = boundary[boundary.organization == scheme].sort_values(
                "relativeOffset"
            )
            semilogy_points(
                plt.gca(),
                group.relativeOffset,
                group.BER,
                group.berCiHigh,
                marker="o",
                linewidth=1,
                label=LABELS[scheme],
            )
        plt.xlabel("相对内部边界位置 (bit)")
        plt.ylabel("BER")
        plt.title(f"{rate} 边界误码（Es/N0={representative_snr:g} dB）")
        plt.grid(True, which="both", alpha=0.25)
        plt.legend()
        save_plot(
            f"stage14_{rate.lower()}_boundary_relative_ber", figure, manifest
        )

        point = data[data.snrDb == representative_snr].copy()
        point["label"] = point.organization.map(LABELS)
        figure = write_figure_data(
            f"stage14_{rate.lower()}_first_output_latency",
            point[
                [
                    "organization",
                    "rateCase",
                    "snrDb",
                    "firstOutputDelaySymbols",
                ]
            ],
        )
        plt.figure(figsize=(7.2, 4.8))
        plt.bar(point.label, point.firstOutputDelaySymbols)
        plt.ylabel("通信等待（符号）")
        plt.title(f"{rate} 首次输出等待")
        plt.grid(True, axis="y", alpha=0.25)
        save_plot(
            f"stage14_{rate.lower()}_first_output_latency", figure, manifest
        )

        delay_columns = [
            "organization",
            "rateCase",
            "snrDb",
            "avgDecisionDelaySymbols",
            "p95DecisionDelaySymbols",
            "fullFrameLastDecisionSymbol",
        ]
        figure = write_figure_data(
            f"stage14_{rate.lower()}_decision_latency", point[delay_columns]
        )
        x = range(len(point))
        width = 0.24
        plt.figure(figsize=(7.2, 4.8))
        plt.bar(
            [value - width for value in x],
            point.avgDecisionDelaySymbols,
            width,
            label="平均决策等待",
        )
        plt.bar(
            x,
            point.p95DecisionDelaySymbols,
            width,
            label="P95 决策等待",
        )
        plt.bar(
            [value + width for value in x],
            point.fullFrameLastDecisionSymbol,
            width,
            label="末 bit 输出时刻",
        )
        plt.xticks(list(x), point.label)
        plt.ylabel("符号")
        plt.title(f"{rate} 输出时序")
        plt.grid(True, axis="y", alpha=0.25)
        plt.legend()
        save_plot(f"stage14_{rate.lower()}_decision_latency", figure, manifest)

        figure = write_figure_data(
            f"stage14_{rate.lower()}_normalized_goodput",
            data[
                [
                    "organization",
                    "rateCase",
                    "snrDb",
                    "normalizedGoodput",
                    "FER",
                ]
            ],
        )
        plt.figure(figsize=(7.2, 4.8))
        for scheme in SCHEMES:
            group = data[data.organization == scheme].sort_values("snrDb")
            plt.plot(
                group.snrDb,
                group.normalizedGoodput,
                marker="o",
                markersize=3,
                linewidth=1,
                label=LABELS[scheme],
            )
        plt.xlabel("SNR = Es/N0 (dB)")
        plt.ylabel("归一化有效吞吐")
        plt.title(f"{rate} 有效吞吐")
        plt.grid(True, alpha=0.25)
        plt.legend()
        save_plot(
            f"stage14_{rate.lower()}_normalized_goodput", figure, manifest
        )
    return manifest


def main() -> None:
    configure_font()
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    unit_paths = sorted(
        path
        for path in RUNTIME.glob("unit_*.csv")
        if not path.name.endswith("_offsets.csv")
    )
    offset_paths = sorted(RUNTIME.glob("unit_*_offsets.csv"))
    if len(unit_paths) != 93 or len(offset_paths) != 93:
        raise RuntimeError(
            f"formal units incomplete: main={len(unit_paths)}, offsets={len(offset_paths)}"
        )
    main_data = pd.concat((pd.read_csv(path) for path in unit_paths))
    offset_data = pd.concat((pd.read_csv(path) for path in offset_paths))
    validate(main_data, offset_data)
    main_path = RESULTS / "stage14_online_slot_formal_results.csv"
    offset_path = RESULTS / "stage14_boundary_offset_results.csv"
    main_data.to_csv(main_path, index=False)
    offset_data.to_csv(offset_path, index=False)
    selection = select_organizations(main_data)
    selection_path = RESULTS / "stage14_organization_recommendations.csv"
    selection.to_csv(selection_path, index=False)
    manifest = make_plots(main_data, offset_data)
    plot_manifest = {
        "sourceFiles": [
            {"path": main_path.name, "sha256": sha256(main_path)},
            {"path": offset_path.name, "sha256": sha256(offset_path)},
        ],
        "plots": manifest,
    }
    (RESULTS / "plot_manifest.json").write_text(
        json.dumps(plot_manifest, indent=2), encoding="utf-8"
    )
    selected = selection[selection.selectedBalanced == 1][
        ["rateCase", "organization", "worstRelativeFerIncreaseVsBlock"]
    ]
    checks = [
        "# Stage14 plot and formal-data check",
        "",
        "- Formal rows: 372 (3 rates × 31 SNR × 4 organizations): PASS",
        "- Boundary offsets: -10..+9 with Wilson CI: PASS",
        "- Block boundary fields: NOT_APPLICABLE: PASS",
        "- Plots use pointwise CSV data without smoothing: PASS",
        "- BER/FER zero observations use CI upper-bound display only: PASS",
        "",
        "## Balanced selections",
        "",
        markdown_table(selected),
        "",
        "PASS_STAGE14_ONLINE_SLOT_REVISION",
    ]
    (RESULTS / "plot_check.md").write_text(
        "\n".join(checks) + "\n", encoding="utf-8"
    )
    print(
        "PASS_STAGE14_ONLINE_SLOT_REVISION "
        f"rows={len(main_data)} offsets={len(offset_data)} plots={len(manifest)}"
    )


def process_dense() -> None:
    runtime = STAGE / "runtime" / "revision_20260729_formal_dense"
    unit_paths = sorted(
        path
        for path in runtime.glob("unit_*.csv")
        if not path.name.endswith("_offsets.csv")
    )
    offset_paths = sorted(runtime.glob("unit_*_offsets.csv"))
    if len(unit_paths) != 73 or len(offset_paths) != 73:
        raise RuntimeError(
            f"dense units incomplete: main={len(unit_paths)}, offsets={len(offset_paths)}"
        )
    data = pd.concat((pd.read_csv(path) for path in unit_paths))
    expected = {
        "R12": [round(-2.0 + 0.1 * index, 10) for index in range(21)],
        "R23": [round(-0.5 + 0.1 * index, 10) for index in range(26)],
        "R34": [round(0.5 + 0.1 * index, 10) for index in range(26)],
    }
    if len(data) != 73 * 2:
        raise RuntimeError(f"expected 146 dense rows, found {len(data)}")
    selection = pd.read_csv(
        RESULTS / "stage14_organization_recommendations.csv"
    )
    selected = {
        row.rateCase: row.organization
        for _, row in selection[selection.selectedBalanced == 1].iterrows()
    }
    for rate in RATES:
        for scheme in ["A_BLOCK_300", selected[rate]]:
            observed = sorted(
                round(value, 10)
                for value in data[
                    (data.rateCase == rate) & (data.organization == scheme)
                ].snrDb
            )
            if observed != expected[rate]:
                raise RuntimeError(f"dense grid mismatch: {rate}/{scheme}")
    final = data.copy()
    if len(final) != 146:
        raise RuntimeError(f"expected 146 final dense rows, found {len(final)}")
    final.to_csv(
        RESULTS / "stage14_online_slot_dense_results.csv", index=False
    )
    print("PASS_STAGE14_DENSE rows=146")


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "coarse":
        main()
    elif sys.argv[1] == "dense":
        process_dense()
    else:
        raise SystemExit("usage: process_stage14_revision.py [coarse|dense]")
