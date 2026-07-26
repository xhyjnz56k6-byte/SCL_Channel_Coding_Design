#!/usr/bin/env python3
"""Generate audited BCH S2 PNG figures and per-figure source tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


STYLES = {
    "BCH-S200": ("#1f77b4", "-", "o", "BCH-S200"),
    "BCH-B200": ("#d62728", "--", "s", "BCH-B200"),
    "BCH-S300": ("#2ca02c", "-.", "^", "BCH-S300"),
    "BCH-B300": ("#9467bd", ":", "D", "BCH-B300"),
    "BCH-B300-426": ("#ff7f0e", "--", "v", "BCH-B300-426"),
}
SYMBOL_ESN0_LABEL = "Symbol Es/N0 (dB)"
TIMING_SCOPE = "EQUALIZATION_HARD_DECISION_ERROR_ACCOUNTING_DECODE_AND_AUDIT"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise SystemExit(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def row_common(row: dict[str, str]) -> dict[str, str]:
    return {
        "sourcePayloadEbN0Db": row.get("sourcePayloadEbN0Db", ""),
        "frameRate": row.get("frameRate", ""),
        "snrDb": row.get("snrDb", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/s2_04_fixed_multipath_mmse"
    formal_path = stage / "formal_summary.csv"
    awgn_path = repo / "Task/BCH/simulation/stages/s2_03_awgn_baseline_reuse/awgn_baseline_snr_converted.csv"
    formal, awgn = read(formal_path), read(awgn_path)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    manifests: list[dict[str, object]] = []

    def finish(name: str, title: str, rows: list[dict[str, object]], source: Path,
               y_column: str, y_label: str, y_scale: str = "linear",
               x_column: str = "snrDb", x_label: str = SYMBOL_ESN0_LABEL,
               x_unit: str = "dB", y_unit: str = "ratio",
               note: str = "") -> None:
        data_path = stage / f"figure_data_{name}.csv"
        png_path = stage / f"{name}.png"
        write(data_path, rows)
        ax = plt.gca()
        labels = [label for label in ax.get_legend_handles_labels()[1] if label and not label.startswith("_")]
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        if note:
            plt.figtext(0.5, 0.01, note, ha="center", fontsize=8)
        if y_scale == "log":
            plt.yscale("log")
        plt.grid(True, which="both", alpha=0.25)
        if labels:
            plt.legend()
        plt.tight_layout(rect=(0.0, 0.04, 1.0, 1.0) if note else None)
        plt.savefig(png_path, dpi=180, format="png")
        plt.close()
        manifests.append({
            "filename": png_path.name,
            "title": title,
            "sourceCsv": source.relative_to(repo).as_posix(),
            "sourceCsvSha256": sha(source),
            "figureDataCsv": data_path.name,
            "figureDataSha256": sha(data_path),
            "xColumn": x_column,
            "xLabel": x_label,
            "xUnit": x_unit,
            "yColumn": y_column,
            "yLabel": y_label,
            "yUnit": y_unit,
            "xTransformFormula": "snrDb=sourcePayloadEbN0Db+10*log10(frameRate)",
            "xSemantic": "physical symbol energy-to-noise-density ratio Es/N0, not generic SNR index",
            "yScale": y_scale,
            "zeroHandlingPolicy": "omit zero observations from logarithmic panels; never replace with epsilon",
            "legendLabels": labels,
            "legendLabelCount": len(labels),
            "uniqueLegendLabelCount": len(set(labels)),
            "totalReceiverTimingScope": TIMING_SCOPE if "receiver_time" in name else "",
            "figureNote": note,
            "caseStyles": {case: {"color": value[0], "lineStyle": value[1], "marker": value[2], "label": value[3]}
                           for case, value in STYLES.items()},
            "dpi": 180,
            "matplotlibVersion": matplotlib.__version__,
            "pngSha256": sha(png_path),
            "generatedBy": "plot_bch_s2_multipath.py",
            "gitCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                                        text=True, stdout=subprocess.PIPE).stdout.strip(),
        })

    def line_plot(payload: int, metric: str, name: str, title: str, ylabel: str,
                  log: bool = False) -> None:
        rows: list[dict[str, object]] = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            selected = sorted((row for row in formal if int(row["payloadLength"]) == payload and
                               row["caseName"] == case and (not log or float(row[metric]) > 0.0)),
                              key=lambda row: float(row["snrDb"]))
            if not selected:
                continue
            color, style, marker, label = STYLES[case]
            plt.plot([float(row["snrDb"]) for row in selected],
                     [float(row[metric]) for row in selected], color=color, linestyle=style,
                     marker=marker, markevery=max(1, len(selected) // 10), label=label)
            rows.extend({"caseName": case, **row_common(row), metric: row[metric]} for row in selected)
        finish(name, title, rows, formal_path, metric, ylabel, "log" if log else "linear")

    for payload in (200, 300):
        prefix = f"bch_s2_{payload}bit"
        title_prefix = f"{payload}-bit BCH"
        line_plot(payload, "BER", f"{prefix}_multipath_ber", f"{title_prefix} multipath BER", "BER", True)
        line_plot(payload, "FER", f"{prefix}_multipath_fer", f"{title_prefix} multipath FER", "FER", True)
        line_plot(payload, "trueSuccessRate", f"{prefix}_true_success", f"{title_prefix} true success rate", "True success rate")
        line_plot(payload, "miscorrectionRate", f"{prefix}_miscorrection", f"{title_prefix} miscorrection rate", "Miscorrection rate", True)
        line_plot(payload, "decoderFailureRate", f"{prefix}_decoder_failure", f"{title_prefix} decoder failure rate", "Decoder failure rate", True)
        line_plot(payload, "avgEqualizationTimeUs", f"{prefix}_equalization_time", f"{title_prefix} MMSE equalization time", "Average equalization time (us)")
        line_plot(payload, "avgDecodeTimeUs", f"{prefix}_decode_time", f"{title_prefix} decode time", "Average decode time (us)")
        line_plot(payload, "avgTotalReceiverTimeUs", f"{prefix}_total_receiver_time", f"{title_prefix} total receiver processing time", "Average total receiver processing time (us)")

        rows = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            selected = sorted((row for row in formal if int(row["payloadLength"]) == payload and row["caseName"] == case),
                              key=lambda row: float(row["snrDb"]))
            if not selected:
                continue
            color, style, marker, label = STYLES[case]
            for metric, suffix, linestyle in [
                ("preEqualizationHardBER", "pre-MMSE", style),
                ("postEqualizationHardBER", "post-MMSE", "--"),
            ]:
                valid = [row for row in selected if float(row[metric]) > 0.0]
                plt.plot([float(row["snrDb"]) for row in valid], [float(row[metric]) for row in valid],
                         color=color, linestyle=linestyle, marker=marker,
                         markevery=max(1, len(valid) // 10), label=f"{label} {suffix}")
                rows.extend({"caseName": case, "series": suffix, **row_common(row), "hardBER": row[metric]}
                            for row in valid)
        finish(f"{prefix}_pre_post_mmse_hard_ber", f"{title_prefix} pre/post-MMSE hard-decision BER",
               rows, formal_path, "hardBER", "Hard-decision BER", "log")

        rows = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            color, style, marker, label = STYLES[case]
            for channel, source_rows, channel_label in [("AWGN", awgn, "AWGN"), ("MULTIPATH", formal, "Multipath+MMSE")]:
                selected = sorted((row for row in source_rows if int(row["payloadLength"]) == payload and
                                   row["caseName"] == case and float(row["FER"]) > 0.0),
                                  key=lambda row: float(row["snrDb"]))
                if not selected:
                    continue
                plt.plot([float(row["snrDb"]) for row in selected], [float(row["FER"]) for row in selected],
                         color=color, linestyle=":" if channel == "AWGN" else style,
                         marker=marker, markevery=max(1, len(selected) // 8), label=f"{label} {channel_label}")
                rows.extend({"caseName": case, "channel": channel, **row_common(row), "FER": row["FER"]}
                            for row in selected)
        finish(f"{prefix}_awgn_vs_multipath_fer", f"{title_prefix} AWGN vs multipath FER",
               rows, formal_path, "FER", "FER", "log")

    loss_path = stage / "multipath_loss_summary.csv"
    loss = [row for row in read(loss_path) if row["valid"] == "true"]
    plt.figure(figsize=(9, 5.4))
    cases = sorted({row["caseName"] for row in loss})
    for index, target in enumerate(["0.1", "0.01", "0.001"]):
        by_case = {row["caseName"]: row for row in loss if str(float(row["targetFer"])) == target}
        x = [i + (index - 1) * 0.22 for i, case in enumerate(cases) if case in by_case]
        y = [float(by_case[case]["multipathLossDb"]) for case in cases if case in by_case]
        plt.bar(x, y, width=0.22, label=f"FER={target}")
    plt.xticks(range(len(cases)), cases, rotation=15)
    finish("bch_s2_multipath_loss_at_target_fer", "Multipath loss at target FER",
           loss, loss_path, "multipathLossDb", "Multipath loss (dB)",
           x_column="caseName", x_label="BCH case", x_unit="case", y_unit="dB")

    source = stage / "fer_amplification_summary.csv"
    source_rows = read(source)
    rows = []
    plt.figure(figsize=(8.4, 5.2))
    for case in STYLES:
        all_case_rows = sorted((row for row in source_rows if row["caseName"] == case),
                               key=lambda row: float(row["snrDb"]))
        selected = [row for row in all_case_rows if row.get("valid") == "true" and
                    row.get("ferAmplification", "") and float(row["ferAmplification"]) > 0.0]
        if selected:
            color, style, marker, label = STYLES[case]
            status = selected[0].get("publicationStatus", "")
            if status == "CURVE_ALLOWED":
                plt.plot([float(row["snrDb"]) for row in selected],
                         [float(row["ferAmplification"]) for row in selected],
                         color=color, linestyle=style, marker=marker,
                         markevery=max(1, len(selected) // 8), label=label)
            elif status == "SINGLE_POINT_ONLY":
                plt.plot([float(row["snrDb"]) for row in selected],
                         [float(row["ferAmplification"]) for row in selected],
                         color=color, linestyle="None", marker=marker, label=f"{label} single point")
        rows.extend({**row, "plotted": str(row in selected).lower()} for row in all_case_rows)
    finish("bch_s2_multipath_fer_amplification",
           "AWGN与多径共同信噪比区间FER比值",
           rows, source, "ferAmplification", "FER比值（多径/AWGN）", "log",
           note="Only real overlapping Es/N0 intervals between AWGN and formal multipath curves are shown.")

    source = stage / "mmse_hard_ber_summary.csv"
    source_rows = read(source)
    rows = []
    plt.figure(figsize=(8.4, 5.2))
    for case in STYLES:
        selected = sorted((row for row in source_rows if row["caseName"] == case and
                           row.get("valid") == "true" and row.get("mmseHardBerReductionRatio", "") and
                           float(row["mmseHardBerReductionRatio"]) > 0.0),
                          key=lambda row: float(row["snrDb"]))
        if not selected:
            continue
        color, style, marker, label = STYLES[case]
        plt.plot([float(row["snrDb"]) for row in selected],
                 [float(row["mmseHardBerReductionRatio"]) for row in selected],
                 color=color, linestyle=style, marker=marker,
                 markevery=max(1, len(selected) // 8), label=label)
        rows.extend(selected)
    finish("bch_s2_mmse_hard_ber_reduction", "MMSE hard-decision BER ratio",
           rows, source, "mmseHardBerReductionRatio", "post-MMSE / pre-MMSE hard BER", "log")

    timing_path = stage / "timing_summary.csv"
    timing = read(timing_path)
    plt.figure(figsize=(9, 5.4))
    cases = [row["caseName"] for row in timing]
    x = list(range(len(cases)))
    plt.bar([v - 0.24 for v in x], [float(row["avgEqualizationTimeUs"]) for row in timing], width=0.24, label="Equalization")
    plt.bar(x, [float(row["avgDecodeTimeUs"]) for row in timing], width=0.24, label="Decode")
    plt.bar([v + 0.24 for v in x], [float(row["avgTotalReceiverTimeUs"]) for row in timing], width=0.24, label="Total receiver")
    plt.xticks(x, cases, rotation=15)
    finish("bch_s2_receiver_time_comparison", "Receiver processing time comparison",
           timing, timing_path, "avgTotalReceiverTimeUs", "Average time (us)",
           x_column="caseName", x_label="BCH case", x_unit="case", y_unit="us",
           note="Total receiver includes equalization, hard decision, error accounting, decode, and audit; bars are not additive independent hardware-module times.")

    (stage / "plot_manifest.json").write_text(
        json.dumps({"schemaVersion": "bch.s2.plot_manifest.v2", "figures": manifests},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = [{
        "filename": item["filename"],
        "figureDataCsv": item["figureDataCsv"],
        "pngMagicValid": (stage / str(item["filename"])).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
        "sourceHashMatch": item["sourceCsvSha256"] == sha(repo / str(item["sourceCsv"])),
        "figureDataHashMatch": item["figureDataSha256"] == sha(stage / str(item["figureDataCsv"])),
        "pngHashMatch": item["pngSha256"] == sha(stage / str(item["filename"])),
        "legendLabelCount": item["legendLabelCount"],
        "uniqueLegendLabelCount": item["uniqueLegendLabelCount"],
        "legendUnique": item["legendLabelCount"] == item["uniqueLegendLabelCount"],
        "xLabel": item["xLabel"],
        "status": "PASS",
    } for item in manifests]
    write(stage / "figure_data_audit.csv", audit)
    if len(manifests) != 24 or any(not all(row[key] for key in
       ["pngMagicValid", "sourceHashMatch", "figureDataHashMatch", "pngHashMatch", "legendUnique"])
       for row in audit):
        raise SystemExit("BLOCKED_BCH_S2_04_FIGURE_DATA_MISMATCH")
    print(f"PASS_BCH_S2_04_PLOTS png={len(manifests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
