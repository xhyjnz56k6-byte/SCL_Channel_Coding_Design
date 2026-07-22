#!/usr/bin/env python3
"""Create the frozen BCH-12 matplotlib PNG set and auditable figure data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plotted_value(row: dict[str, str], metric: str) -> tuple[float, str]:
    raw = float(row[metric])
    if raw > 0.0:
        return raw, "RAW_POSITIVE"
    denominator = float(row["processedPayloadBits"] if metric == "BER" else row["processedFrames"])
    return 3.0 / denominator, "RULE_OF_THREE_UPPER_BOUND_FOR_ZERO_OBSERVATION"


def line_plot(rows: list[dict[str, str]], metric: str, filename: str, output: Path,
              ylabel: str, log_scale: bool, manifest: list[dict[str, object]],
              audit: list[dict[str, object]]) -> None:
    if Path(filename).suffix.lower() != ".png":
        raise ValueError("BCH plot output must end in .png")
    figure_rows: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(10.0, 5.5))
    try:
        for case in CASES:
            selected = sorted((row for row in rows if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
            x_values: list[float] = []
            y_values: list[float] = []
            for row in selected:
                raw = float(row[metric])
                if log_scale:
                    shown, policy = plotted_value(row, metric)
                else:
                    shown, policy = raw, "RAW_LINEAR"
                x_values.append(float(row["ebn0Db"]))
                y_values.append(shown)
                figure_rows.append({"caseName": case, "ebn0Db": row["ebn0Db"], "metric": metric,
                                    "rawValue": raw, "plottedValue": shown, "zeroHandlingPolicy": policy})
                audit.append({"filename": filename, "caseName": case, "ebn0Db": row["ebn0Db"],
                              "metric": metric, "rawValue": raw, "plottedValue": shown,
                              "zeroHandlingPolicy": policy})
            axis.plot(x_values, y_values, marker="o", label=case)
        axis.set_title(f"BCH-12 smoke {ylabel}")
        axis.set_xlabel("Payload Eb/N0 (dB)")
        axis.set_ylabel(ylabel)
        if log_scale:
            axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend()
        target = output / filename
        fig.savefig(target, dpi=220, bbox_inches="tight")
    finally:
        plt.close(fig)
    data_path = output / f"figure_data_{Path(filename).stem}.csv"
    write_rows(data_path, ["caseName", "ebn0Db", "metric", "rawValue", "plottedValue", "zeroHandlingPolicy"], figure_rows)
    manifest.append({"filename": filename, "sourceCsv": "awgn_smoke_summary.csv", "figureDataCsv": data_path.name,
                     "sha256": sha256(output / filename), "dpi": 220, "xColumn": "ebn0Db", "yColumn": metric,
                     "logScale": log_scale, "zeroHandlingPolicy": "RULE_OF_THREE_IF_ZERO" if log_scale else "RAW_LINEAR",
                     "generatedBy": "plot_bch_smoke.py", "matplotlibVersion": matplotlib.__version__})


def status_plot(rows: list[dict[str, str]], output: Path, manifest: list[dict[str, object]],
                audit: list[dict[str, object]]) -> None:
    filename = "bch12_smoke_status.png"
    metrics = ["reportedSuccessRate", "miscorrectionRate", "decoderFailureRate"]
    figure_rows: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(8.0, 5.2))
    try:
        for metric in metrics:
            for case in CASES:
                selected = sorted((row for row in rows if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
                x_values = [float(row["ebn0Db"]) for row in selected]
                y_values = [float(row[metric]) for row in selected]
                axis.plot(x_values, y_values, marker="o", label=f"{case} {metric}")
                for row, shown in zip(selected, y_values):
                    item = {"caseName": case, "ebn0Db": row["ebn0Db"], "metric": metric,
                            "rawValue": shown, "plottedValue": shown, "zeroHandlingPolicy": "RAW_LINEAR"}
                    figure_rows.append(item)
                    audit.append({"filename": filename, **item})
        axis.set_title("BCH-12 decoder status rates")
        axis.set_xlabel("Payload Eb/N0 (dB)")
        axis.set_ylabel("Rate")
        axis.set_ylim(-0.02, 1.02)
        axis.grid(True, alpha=0.3)
        axis.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=7)
        fig.savefig(output / filename, dpi=220, bbox_inches="tight")
    finally:
        plt.close(fig)
    data_path = output / "figure_data_bch12_smoke_status.csv"
    write_rows(data_path, ["caseName", "ebn0Db", "metric", "rawValue", "plottedValue", "zeroHandlingPolicy"], figure_rows)
    manifest.append({"filename": filename, "sourceCsv": "awgn_smoke_summary.csv", "figureDataCsv": data_path.name,
                     "sha256": sha256(output / filename), "dpi": 220, "xColumn": "ebn0Db",
                     "yColumn": ";".join(metrics), "logScale": False, "zeroHandlingPolicy": "RAW_LINEAR",
                     "generatedBy": "plot_bch_smoke.py", "matplotlibVersion": matplotlib.__version__})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.summary)
    if len(rows) != 20:
        raise SystemExit("BCH-12 summary must contain 20 case-points")
    manifest: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    line_plot(rows, "BER", "bch12_smoke_ber.png", args.output_dir, "Payload BER", True, manifest, audit)
    line_plot(rows, "FER", "bch12_smoke_fer.png", args.output_dir, "Payload FER", True, manifest, audit)
    line_plot(rows, "trueSuccessRate", "bch12_smoke_true_success.png", args.output_dir, "True success rate", False, manifest, audit)
    status_plot(rows, args.output_dir, manifest, audit)
    (args.output_dir / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_rows(args.output_dir / "figure_data_audit.csv",
               ["filename", "caseName", "ebn0Db", "metric", "rawValue", "plottedValue", "zeroHandlingPolicy"], audit)
    forbidden = [path for path in args.output_dir.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if forbidden:
        raise SystemExit("BLOCKED_BCH_PLOT_NON_PNG_ARTIFACT")
    for item in manifest:
        path = args.output_dir / str(item["filename"])
        if path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("invalid PNG artifact")
    print(f"PASS_BCH12_PLOT_AUDIT png={len(manifest)} matplotlib={matplotlib.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
