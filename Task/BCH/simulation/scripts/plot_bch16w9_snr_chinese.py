#!/usr/bin/env python3
"""Create and audit the six BCH16W9 Chinese SNR figures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE_ORDER = {
    200: ["BCH-S200", "BCH-B200"],
    300: ["BCH-S300", "BCH-B300", "BCH-B300-426"],
}
CASE_STYLE = {
    "BCH-S200": ("分段 BCH(15,11)", "#1f77b4", "o", "-"),
    "BCH-B200": ("缩短 BCH(255,207)", "#d62728", "s", "--"),
    "BCH-S300": ("分段 BCH(15,11)", "#1f77b4", "o", "-"),
    "BCH-B300": ("缩短 BCH(511,421)", "#d62728", "s", "--"),
    "BCH-B300-426": ("缩短 BCH(511,385)", "#2ca02c", "D", "-."),
}
METRIC_CONFIG = {
    "BER": ("误码率对比", "误码率（BER）", True),
    "FER": ("误帧率对比", "误帧率（FER）", True),
    "avgDecodeTimeUs": ("平均译码时延", "平均译码时延（μs）", False),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snr_db(ebn0_db: float, rate: float) -> float:
    return ebn0_db + 10.0 * math.log10(rate)


def make_figure(
    payload: int,
    metric: str,
    rows: list[dict[str, object]],
    output: Path,
) -> dict[str, object]:
    suffix = {"BER": "ber", "FER": "fer", "avgDecodeTimeUs": "decode_time"}[metric]
    filename = f"bch_{payload}bit_{suffix}_snr_cn.png"
    data_filename = f"figure_data_{Path(filename).stem}.csv"
    title_suffix, y_label, log_scale = METRIC_CONFIG[metric]
    title = f"{payload}比特BCH{title_suffix}"

    figure_data: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(10.0, 6.0))
    try:
        for case_name in CASE_ORDER[payload]:
            case_rows = sorted(
                (row for row in rows if row["caseName"] == case_name),
                key=lambda row: float(row["snrDb"]),
            )
            if not case_rows:
                raise SystemExit(f"BLOCKED_BCH16W9_MISSING_CASE_DATA: {case_name}")
            label, color, marker, linestyle = CASE_STYLE[case_name]
            x_values = [float(row["snrDb"]) for row in case_rows]
            y_values = [float(row[metric]) for row in case_rows]
            if any(not math.isfinite(value) or value <= 0.0 for value in y_values):
                raise SystemExit(f"BLOCKED_BCH16W9_INVALID_PLOT_VALUE: {case_name}/{metric}")
            axis.plot(
                x_values,
                y_values,
                color=color,
                marker=marker,
                linestyle=linestyle,
                linewidth=2.0,
                markersize=5.0,
                label=label,
            )
            for row in case_rows:
                figure_data.append({
                    "caseName": case_name,
                    "legend": label,
                    "sourceEbN0Db": row["sourceEbN0Db"],
                    "frameRate": row["frameRate"],
                    "snrDb": row["snrDb"],
                    metric: row[metric],
                })
        axis.set_title(title, fontsize=16)
        axis.set_xlabel("SNR（dB）", fontsize=13)
        axis.set_ylabel(y_label, fontsize=13)
        if log_scale:
            axis.set_yscale("log")
            axis.grid(True, which="both", alpha=0.28)
        else:
            axis.grid(True, alpha=0.28)
        axis.tick_params(labelsize=11)
        axis.legend(fontsize=11, framealpha=0.95)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally:
        plt.close(fig)

    write_rows(output / data_filename, figure_data)
    return {
        "filename": filename,
        "figureDataCsv": data_filename,
        "payloadLength": payload,
        "metric": metric,
        "title": title,
        "xLabel": "SNR（dB）",
        "yLabel": y_label,
        "xColumn": "snrDb",
        "sourceXColumn": "sourceEbN0Db",
        "snrFormula": "snrDb=sourceEbN0Db+10*log10(frameRate)",
        "logScale": log_scale,
        "sha256": sha256(output / filename),
        "dpi": 240,
        "matplotlibVersion": matplotlib.__version__,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-summary", type=Path, required=True)
    parser.add_argument("--timing-summary", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()

    figures_dir = args.stage_dir / "figures"
    if figures_dir.exists():
        raise SystemExit(f"BLOCKED_BCH16W9_FIGURES_ALREADY_EXIST: {figures_dir}")
    figures_dir.mkdir(parents=True)
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
    })

    formal = read_rows(args.formal_summary)
    timing = read_rows(args.timing_summary)
    if len(formal) != 74 or len(timing) != len(formal):
        raise SystemExit(
            f"BLOCKED_BCH16W9_POINT_COUNT formal={len(formal)} timing={len(timing)}"
        )

    timing_by_key = {
        (row["caseName"], row["sourceEbN0Db"]): row for row in timing
    }
    if len(timing_by_key) != len(timing):
        raise SystemExit("BLOCKED_BCH16W9_DUPLICATE_TIMING_POINT")

    combined: list[dict[str, object]] = []
    timing_point_rows: list[dict[str, object]] = []
    for row in formal:
        key = (row["caseName"], row["ebn0Db"])
        if key not in timing_by_key:
            raise SystemExit(f"BLOCKED_BCH16W9_MISSING_TIMING_POINT: {key}")
        timed = timing_by_key[key]
        if (
            row["payloadLength"] != timed["payloadLength"]
            or row["encodedLength"] != timed["encodedLength"]
            or abs(float(row["frameRate"]) - float(timed["frameRate"])) > 1e-15
        ):
            raise SystemExit(f"BLOCKED_BCH16W9_TIMING_SOURCE_MISMATCH: {key}")
        converted = snr_db(float(row["ebn0Db"]), float(row["frameRate"]))
        if not math.isfinite(converted):
            raise SystemExit(f"BLOCKED_BCH16W9_NONFINITE_SNR: {key}")
        combined.append({
            "caseName": row["caseName"],
            "payloadLength": row["payloadLength"],
            "encodedLength": row["encodedLength"],
            "frameRate": row["frameRate"],
            "sourceEbN0Db": row["ebn0Db"],
            "snrDb": format(converted, ".17g"),
            "BER": row["BER"],
            "FER": row["FER"],
            "avgDecodeTimeUs": timed["publishedAvgDecodeTimeUs"],
        })
        timing_point_rows.append({
            **timed,
            "snrDb": format(converted, ".17g"),
        })

    manifests: list[dict[str, object]] = []
    for payload in (200, 300):
        for metric in ("BER", "FER", "avgDecodeTimeUs"):
            manifests.append(make_figure(payload, metric, combined, figures_dir))
    (figures_dir / "plot_manifest.json").write_text(
        json.dumps(manifests, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_rows(args.stage_dir / "timing_point_summary.csv", timing_point_rows)

    correction_rows: list[dict[str, object]] = []
    for case_name in CASE_STYLE:
        source_rows = [row for row in formal if row["caseName"] == case_name]
        weights = [int(row["processedFrames"]) for row in source_rows]
        old_values = [float(row["avgDecodeTimeUs"]) for row in source_rows]
        new_values = [
            float(timing_by_key[(row["caseName"], row["ebn0Db"])]["publishedAvgDecodeTimeUs"])
            for row in source_rows
        ]
        total_weight = sum(weights)
        old_weighted = sum(value * weight for value, weight in zip(old_values, weights)) / total_weight
        new_weighted = sum(value * weight for value, weight in zip(new_values, weights)) / total_weight
        correction_rows.append({
            "caseName": case_name,
            "pointCount": len(source_rows),
            "sourceProcessedFrames": total_weight,
            "oldWeightedAvgDecodeTimeUs": format(old_weighted, ".17g"),
            "newWeightedAvgDecodeTimeUs": format(new_weighted, ".17g"),
            "newOverOldRatio": format(new_weighted / old_weighted, ".17g"),
            "removedTimingPollutionUs": format(old_weighted - new_weighted, ".17g"),
        })
    write_rows(args.stage_dir / "result_summary.csv", correction_rows)

    # Machine-check the exact SNR conversion and preservation of BER/FER values.
    source_by_key = {
        (row["caseName"], row["ebn0Db"]): row for row in formal
    }
    for row in combined:
        source = source_by_key[(str(row["caseName"]), str(row["sourceEbN0Db"]))]
        expected = snr_db(float(source["ebn0Db"]), float(source["frameRate"]))
        if abs(float(row["snrDb"]) - expected) > 1e-12:
            raise SystemExit("BLOCKED_BCH16W9_SNR_CONVERSION_MISMATCH")
        if float(row["BER"]) != float(source["BER"]) or float(row["FER"]) != float(source["FER"]):
            raise SystemExit("BLOCKED_BCH16W9_PERFORMANCE_VALUE_CHANGED")
    if len(manifests) != 6:
        raise SystemExit("BLOCKED_BCH16W9_FIGURE_COUNT")
    for item in manifests:
        image = figures_dir / str(item["filename"])
        if image.stat().st_size < 1000 or image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("BLOCKED_BCH16W9_INVALID_PNG")
        if item["xLabel"] != "SNR（dB）" or "Payload" in str(item) or "Eb/N0" in str(item["xLabel"]):
            raise SystemExit("BLOCKED_BCH16W9_FORBIDDEN_AXIS_TEXT")

    print(
        f"PASS_BCH16W9_SNR_CHINESE_FIGURES figures={len(manifests)} "
        f"points={len(combined)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
