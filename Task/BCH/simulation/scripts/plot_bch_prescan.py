#!/usr/bin/env python3
"""Create the frozen BCH-13 matplotlib-only PNG set."""

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


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, values: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader(); writer.writerows(values)


def make_plot(all_rows: list[dict[str, str]], cases: list[str], metric: str, filename: str,
              ylabel: str, log_scale: bool, output: Path, manifest: list[dict[str, object]],
              audit: list[dict[str, object]]) -> None:
    if Path(filename).suffix.lower() != ".png":
        raise ValueError("BCH plot output must end in .png")
    fig, axis = plt.subplots(figsize=(9.0, 5.4))
    data: list[dict[str, object]] = []
    try:
        for case in cases:
            selected = sorted((row for row in all_rows if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
            x_values: list[float] = []
            y_values: list[float] = []
            for row in selected:
                raw = float(row[metric])
                if log_scale and raw == 0.0:
                    denominator = float(row["processedPayloadBits"] if metric == "BER" else row["processedFrames"])
                    shown = 3.0 / denominator
                    policy = "RULE_OF_THREE_UPPER_BOUND_FOR_ZERO_OBSERVATION"
                else:
                    shown = raw
                    policy = "RAW_POSITIVE" if log_scale else "RAW_LINEAR"
                item = {"caseName": case, "ebn0Db": row["ebn0Db"], "metric": metric,
                        "rawValue": raw, "plottedValue": shown, "zeroHandlingPolicy": policy}
                data.append(item); audit.append({"filename": filename, **item})
                x_values.append(float(row["ebn0Db"])); y_values.append(shown)
            axis.plot(x_values, y_values, marker="o", markersize=3, label=case)
        axis.set_title(f"BCH-13 prescan {ylabel}")
        axis.set_xlabel("Payload Eb/N0 (dB)")
        axis.set_ylabel(ylabel)
        if log_scale: axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend()
        fig.savefig(output / filename, dpi=220, bbox_inches="tight")
    finally:
        plt.close(fig)
    data_path = output / f"figure_data_{Path(filename).stem}.csv"
    write_csv(data_path, data)
    manifest.append({"filename": filename, "sourceCsv": "prescan_summary.csv", "figureDataCsv": data_path.name,
                     "sha256": sha256(output / filename), "dpi": 220, "xColumn": "ebn0Db", "yColumn": metric,
                     "logScale": log_scale, "zeroHandlingPolicy": "RULE_OF_THREE_IF_ZERO" if log_scale else "RAW_LINEAR",
                     "generatedBy": "plot_bch_prescan.py", "matplotlibVersion": matplotlib.__version__})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    values = rows(args.summary)
    if len(values) != 84:
        raise SystemExit("BCH-13 summary must contain 84 case-points")
    manifest: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    make_plot(values, ["BCH-S200", "BCH-B200"], "BER", "bch13_prescan_200bit_ber.png", "200-bit payload BER", True, args.output_dir, manifest, audit)
    make_plot(values, ["BCH-S200", "BCH-B200"], "FER", "bch13_prescan_200bit_fer.png", "200-bit payload FER", True, args.output_dir, manifest, audit)
    make_plot(values, ["BCH-S300", "BCH-B300"], "BER", "bch13_prescan_300bit_ber.png", "300-bit payload BER", True, args.output_dir, manifest, audit)
    make_plot(values, ["BCH-S300", "BCH-B300"], "FER", "bch13_prescan_300bit_fer.png", "300-bit payload FER", True, args.output_dir, manifest, audit)
    make_plot(values, CASES, "miscorrectionRate", "bch13_prescan_miscorrection.png", "Miscorrection rate", True, args.output_dir, manifest, audit)
    make_plot(values, CASES, "avgDecodeTimeUs", "bch13_prescan_decode_time.png", "Average decode time (us)", False, args.output_dir, manifest, audit)
    (args.output_dir / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_csv(args.output_dir / "figure_data_audit.csv", audit)
    forbidden = [path for path in args.output_dir.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if forbidden: raise SystemExit("BLOCKED_BCH_PLOT_NON_PNG_ARTIFACT")
    for item in manifest:
        path = args.output_dir / str(item["filename"])
        if path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("invalid PNG artifact")
    print(f"PASS_BCH13_PLOT_AUDIT png={len(manifest)} matplotlib={matplotlib.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
