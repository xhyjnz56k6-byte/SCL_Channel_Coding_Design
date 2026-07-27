#!/usr/bin/env python3
"""Generate audited BCH S2 PNG figures and per-figure source tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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
SNR_LABEL = "SNR (dB)"
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


def finite_float(value: object, context: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED_BCH_S2_04_NONFINITE_VALUE: {context}") from exc
    if not math.isfinite(number):
        raise SystemExit(f"BLOCKED_BCH_S2_04_NONFINITE_VALUE: {context}")
    return number


def validate_figure_rows(name: str, rows: list[dict[str, object]], x_column: str,
                         y_column: str, y_scale: str) -> dict[str, int]:
    if not rows:
        raise SystemExit(f"BLOCKED_BCH_S2_04_EMPTY_FIGURE_DATA: {name}")
    plotted_count = 0
    omitted_count = 0
    for index, row in enumerate(rows, start=1):
        plotted = str(row.get("plotted", "true")).lower() != "false"
        if plotted:
            plotted_count += 1
        else:
            omitted_count += 1
        if x_column == "snrDb":
            snr = finite_float(row.get("snrDb", ""), f"{name}:{index}:snrDb")
            source_ebn0 = row.get("sourcePayloadEbN0Db", "")
            frame_rate = row.get("frameRate", "")
            if source_ebn0 != "" and frame_rate != "":
                expected = finite_float(source_ebn0, f"{name}:{index}:sourcePayloadEbN0Db")
                rate = finite_float(frame_rate, f"{name}:{index}:frameRate")
                if rate <= 0.0:
                    raise SystemExit(f"BLOCKED_BCH_S2_04_X_FORMULA_INVALID_RATE: {name}:{index}")
                expected += 10.0 * math.log10(rate)
                if abs(snr - expected) > 5e-10:
                    raise SystemExit(f"BLOCKED_BCH_S2_04_X_FORMULA_MISMATCH: {name}:{index}")
        if not plotted and (row.get(y_column, "") == "" or str(row.get("valid", "")).lower() == "false"):
            continue
        if y_column not in row or row.get(y_column, "") == "":
            raise SystemExit(f"BLOCKED_BCH_S2_04_Y_VALUE_MISSING: {name}:{index}:{y_column}")
        y_value = finite_float(row[y_column], f"{name}:{index}:{y_column}")
        if y_scale == "log" and y_value <= 0.0:
            raise SystemExit(f"BLOCKED_BCH_S2_04_LOG_Y_NONPOSITIVE: {name}:{index}:{y_column}")
    if plotted_count == 0:
        raise SystemExit(f"BLOCKED_BCH_S2_04_NO_PLOTTED_POINTS: {name}")
    return {"validatedDataPointCount": plotted_count, "omittedRowCount": omitted_count}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[6])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse"
    formal_path = stage / "formal_summary.csv"
    awgn_path = repo / "Task/BCH/simulation/stages/S2-test/s2_03_awgn_baseline_reuse/awgn_baseline_snr_converted.csv"
    formal, awgn = read(formal_path), read(awgn_path)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    manifests: list[dict[str, object]] = []

    def finish(name: str, title: str, rows: list[dict[str, object]], source: Path,
               y_column: str, y_label: str, y_scale: str = "linear",
               x_column: str = "snrDb", x_label: str = SNR_LABEL,
               x_unit: str = "dB", y_unit: str = "ratio",
               note: str = "") -> None:
        if name == "bch_s2_multipath_fer_amplification":
            title = "AWGN与多径重叠区间误帧率放大倍数"
            y_label = "误帧率放大倍数"
            note = "仅绘制AWGN与正式多径结果真实重叠的SNR区间；无重叠点不绘制曲线。"
        validation = validate_figure_rows(name, rows, x_column, y_column, y_scale)
        data_path = stage / f"figure_data_{name}.csv"
        png_path = stage / f"{name}.png"
        write(data_path, rows)
        ax = plt.gca()
        labels = [label for label in ax.get_legend_handles_labels()[1] if label and not label.startswith("_")]
        if len(labels) != len(set(labels)):
            raise SystemExit(f"BLOCKED_BCH_S2_04_LEGEND_LABEL_DUPLICATE: {name}")
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
            "xTransformFormula": "snrDb=sourcePayloadEbN0Db+10*log10(frameRate); normalized waveform SNR uses Bn=Rs",
            "xSemantic": "normalized waveform SNR Ps/Pn with unit-energy symbols and equivalent noise bandwidth Bn=Rs",
            "yScale": y_scale,
            "zeroHandlingPolicy": "omit zero observations from logarithmic panels; never replace with epsilon",
            "legendLabels": labels,
            "legendLabelCount": len(labels),
            "uniqueLegendLabelCount": len(set(labels)),
            **validation,
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
        title_prefix = f"{payload}比特 BCH"
        line_plot(payload, "BER", f"{prefix}_multipath_ber", f"{title_prefix}误码率对比", "误码率 BER", True)
        line_plot(payload, "FER", f"{prefix}_multipath_fer", f"{title_prefix}误帧率对比", "误帧率 FER", True)
        line_plot(payload, "trueSuccessRate", f"{prefix}_true_success", f"{title_prefix}真实成功率对比", "真实成功率")
        line_plot(payload, "miscorrectionRate", f"{prefix}_miscorrection", f"{title_prefix}误纠率对比", "误纠率", True)
        line_plot(payload, "decoderFailureRate", f"{prefix}_decoder_failure", f"{title_prefix}译码失败率对比", "译码失败率", True)
        line_plot(payload, "avgEqualizationTimeUs", f"{prefix}_equalization_time", f"{title_prefix}均衡时延对比", "平均均衡时延 (μs)")
        line_plot(payload, "avgDecodeTimeUs", f"{prefix}_decode_time", f"{title_prefix}译码时延对比", "平均译码时延 (μs)")
        line_plot(payload, "avgTotalReceiverTimeUs", f"{prefix}_total_receiver_time", f"{title_prefix}接收机总时延对比", "平均接收机总时延 (μs)")

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
        finish(f"{prefix}_pre_post_mmse_hard_ber", f"{title_prefix} MMSE前后硬判决误码率",
               rows, formal_path, "hardBER", "硬判决误码率", "log")

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
        finish(f"{prefix}_awgn_vs_multipath_fer", f"{title_prefix} AWGN与多径误帧率对比",
               rows, formal_path, "FER", "误帧率 FER", "log")

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
    finish("bch_s2_multipath_loss_at_target_fer", "目标误帧率下的多径损失",
           loss, loss_path, "multipathLossDb", "多径损失 (dB)",
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
           note="仅绘制AWGN与正式多径结果真实重叠的SNR区间；无重叠点不绘制曲线。")

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
    finish("bch_s2_mmse_hard_ber_reduction", "MMSE硬判决误码率变化倍数",
           rows, source, "mmseHardBerReductionRatio", "MMSE后/前硬判决误码率倍数", "log")

    timing_path = stage / "timing_summary.csv"
    timing = read(timing_path)
    plt.figure(figsize=(9, 5.4))
    cases = [row["caseName"] for row in timing]
    x = list(range(len(cases)))
    plt.bar([v - 0.24 for v in x], [float(row["avgEqualizationTimeUs"]) for row in timing], width=0.24, label="均衡")
    plt.bar(x, [float(row["avgDecodeTimeUs"]) for row in timing], width=0.24, label="译码")
    plt.bar([v + 0.24 for v in x], [float(row["avgTotalReceiverTimeUs"]) for row in timing], width=0.24, label="接收机总时延")
    plt.xticks(x, cases, rotation=15)
    finish("bch_s2_receiver_time_comparison", "BCH接收机处理时延对比",
           timing, timing_path, "avgTotalReceiverTimeUs", "平均时延 (μs)",
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
        "validatedDataPointCount": item["validatedDataPointCount"],
        "omittedRowCount": item["omittedRowCount"],
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
