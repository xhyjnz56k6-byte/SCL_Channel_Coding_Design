#!/usr/bin/env python3
"""Generate and audit the BCH-15 formal matplotlib PNG set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle: return list(csv.DictReader(handle))


def write_rows(path: Path, values: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0])); writer.writeheader(); writer.writerows(values)


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def line_plot(rows: list[dict[str, str]], cases: list[str], metric: str, filename: str, ylabel: str,
              log_scale: bool, output: Path, manifest: list[dict[str, object]], audit: list[dict[str, object]]) -> None:
    if Path(filename).suffix.lower() != ".png": raise ValueError("BCH plot output must end in .png")
    fig, axis = plt.subplots(figsize=(9.0, 5.4)); data: list[dict[str, object]] = []
    try:
        for case in cases:
            selected = sorted((row for row in rows if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
            x_values: list[float] = []; y_values: list[float] = []
            for row in selected:
                raw = float(row[metric])
                if log_scale and raw == 0.0:
                    if metric == "FER": shown = float(row["ferUpper95RuleOfThree"])
                    elif metric == "BER": shown = 3.0 / float(row["processedPayloadBits"])
                    else: shown = 3.0 / float(row["processedFrames"])
                    policy = "RULE_OF_THREE_UPPER_BOUND_FOR_ZERO_OBSERVATION"
                else:
                    shown = raw; policy = "RAW_POSITIVE" if log_scale else "RAW_LINEAR"
                item = {"caseName": case, "ebn0Db": row["ebn0Db"], "metric": metric, "rawValue": raw,
                        "plottedValue": shown, "zeroHandlingPolicy": policy}
                data.append(item); audit.append({"filename": filename, **item})
                x_values.append(float(row["ebn0Db"])); y_values.append(shown)
            axis.plot(x_values, y_values, marker="o", markersize=3, label=case)
        axis.set_title(f"BCH-15 formal {ylabel}"); axis.set_xlabel("Payload Eb/N0 (dB)"); axis.set_ylabel(ylabel)
        if log_scale: axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3); axis.legend(); fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally: plt.close(fig)
    data_path = output / f"figure_data_{Path(filename).stem}.csv"; write_rows(data_path, data)
    manifest.append({"filename": filename, "sourceCsv": "formal_summary.csv", "figureDataCsv": data_path.name,
                     "sha256": sha(output / filename), "dpi": 240, "xColumn": "ebn0Db", "yColumn": metric,
                     "logScale": log_scale, "zeroHandlingPolicy": "RULE_OF_THREE_IF_ZERO" if log_scale else "RAW_LINEAR",
                     "generatedBy": "plot_bch_formal.py", "matplotlibVersion": matplotlib.__version__})


def bar_plot(rows: list[dict[str, str]], filename: str, kind: str, output: Path,
             manifest: list[dict[str, object]], audit: list[dict[str, object]]) -> None:
    fig, axis = plt.subplots(figsize=(9.0, 5.4)); data: list[dict[str, object]] = []
    try:
        if kind == "stop":
            reasons = sorted({row["stopReason"] for row in rows}); width = 0.8 / len(reasons); x = list(range(len(CASES)))
            for index, reason in enumerate(reasons):
                values = [sum(1 for row in rows if row["caseName"] == case and row["stopReason"] == reason) for case in CASES]
                axis.bar([value + index * width for value in x], values, width=width, label=reason)
                for case, value in zip(CASES, values): data.append({"caseName": case, "category": reason, "value": value})
            axis.set_xticks([value + width * (len(reasons) - 1) / 2 for value in x], CASES); axis.set_ylabel("Case-point count")
            axis.set_title("BCH-15 stop reason distribution"); axis.legend()
        else:
            metrics = ["noErrorStatusFrames", "correctedStatusFrames", "failedStatusFrames"]
            bottom = [0] * len(CASES); x = list(range(len(CASES)))
            for metric in metrics:
                values = [sum(int(row[metric]) for row in rows if row["caseName"] == case) for case in CASES]
                axis.bar(x, values, bottom=bottom, label=metric); bottom = [a + b for a, b in zip(bottom, values)]
                for case, value in zip(CASES, values): data.append({"caseName": case, "category": metric, "value": value})
            axis.set_xticks(x, CASES); axis.set_ylabel("Frame count"); axis.set_title("BCH-15 decoder status distribution"); axis.legend()
        axis.grid(True, axis="y", alpha=0.3); fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally: plt.close(fig)
    data_path = output / f"figure_data_{Path(filename).stem}.csv"; write_rows(data_path, data)
    for item in data: audit.append({"filename": filename, "caseName": item["caseName"], "ebn0Db": "",
                                    "metric": item["category"], "rawValue": item["value"],
                                    "plottedValue": item["value"], "zeroHandlingPolicy": "RAW_LINEAR"})
    manifest.append({"filename": filename, "sourceCsv": "formal_summary.csv", "figureDataCsv": data_path.name,
                     "sha256": sha(output / filename), "dpi": 240, "xColumn": "caseName", "yColumn": "value",
                     "logScale": False, "zeroHandlingPolicy": "RAW_LINEAR", "generatedBy": "plot_bch_formal.py",
                     "matplotlibVersion": matplotlib.__version__})


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--summary", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True); rows = read_rows(args.summary)
    manifest: list[dict[str, object]] = []; audit: list[dict[str, object]] = []
    for payload, cases in [(200, ["BCH-S200", "BCH-B200"]), (300, ["BCH-S300", "BCH-B300"])]:
        prefix = f"bch_{payload}bit"
        line_plot(rows, cases, "BER", f"{prefix}_ber_vs_ebn0.png", f"{payload}-bit payload BER", True, args.output_dir, manifest, audit)
        line_plot(rows, cases, "FER", f"{prefix}_fer_vs_ebn0.png", f"{payload}-bit payload FER", True, args.output_dir, manifest, audit)
        line_plot(rows, cases, "trueSuccessRate", f"{prefix}_true_success_vs_ebn0.png", "True success rate", False, args.output_dir, manifest, audit)
        line_plot(rows, cases, "reportedSuccessRate", f"{prefix}_reported_success_vs_ebn0.png", "Reported success rate", False, args.output_dir, manifest, audit)
        line_plot(rows, cases, "miscorrectionRate", f"{prefix}_miscorrection_vs_ebn0.png", "Miscorrection rate", True, args.output_dir, manifest, audit)
        line_plot(rows, cases, "avgDecodeTimeUs", f"{prefix}_decode_time_vs_ebn0.png", "Average decode time (us)", False, args.output_dir, manifest, audit)
    line_plot(rows, CASES, "processedFrames", "bch_all_cases_processed_frames.png", "Processed frames", False, args.output_dir, manifest, audit)
    bar_plot(rows, "bch_all_cases_stop_reason.png", "stop", args.output_dir, manifest, audit)
    bar_plot(rows, "bch_decoder_status_distribution.png", "status", args.output_dir, manifest, audit)
    (args.output_dir / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_rows(args.output_dir / "figure_data_audit.csv", audit)
    forbidden = [path for path in args.output_dir.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if forbidden: raise SystemExit("BLOCKED_BCH15_NON_PNG_PLOT")
    if len(manifest) != 15: raise SystemExit("BCH-15 plot count mismatch")
    for item in manifest:
        path = args.output_dir / str(item["filename"])
        if path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n": raise SystemExit("invalid formal PNG")
    print(f"PASS_BCH15_PLOT_AUDIT png=15 matplotlib={matplotlib.__version__}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
