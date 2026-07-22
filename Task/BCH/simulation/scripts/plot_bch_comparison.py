#!/usr/bin/env python3
"""Generate and audit the four BCH-16 comparison PNG figures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle: return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def save_performance(formal: list[dict[str, str]], payload: int, output: Path, manifest: list[dict[str, object]]) -> None:
    filename = f"bch_{payload}bit_rate_performance_comparison.png"
    cases = [f"BCH-S{payload}", f"BCH-B{payload}"]; figure_data: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(9.0, 5.4))
    try:
        for case in cases:
            rows = sorted((row for row in formal if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
            x = [float(row["ebn0Db"]) for row in rows]; y = [float(row["FER"]) for row in rows]
            axis.plot(x, y, marker="o", markersize=3, label=f"{case} (R={float(rows[0]['frameRate']):.4f})")
            figure_data.extend({"caseName": case, "ebn0Db": a, "FER": b, "frameRate": rows[0]["frameRate"]} for a, b in zip(x, y))
        axis.set_title(f"BCH-16 {payload}-bit segmented vs block AWGN performance")
        axis.set_xlabel("Payload Eb/N0 (dB)"); axis.set_ylabel("Payload FER"); axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3); axis.legend(); fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally: plt.close(fig)
    data_name = f"figure_data_{Path(filename).stem}.csv"; write_rows(output / data_name, figure_data)
    manifest.append({"filename": filename, "sourceCsv": "formal_summary.csv", "figureDataCsv": data_name,
                     "sha256": sha(output / filename), "dpi": 240, "xColumn": "ebn0Db", "yColumn": "FER",
                     "logScale": True, "zeroHandlingPolicy": "NO_ZERO_OBSERVATIONS",
                     "generatedBy": "plot_bch_comparison.py", "matplotlibVersion": matplotlib.__version__})


def save_timing(formal: list[dict[str, str]], output: Path, manifest: list[dict[str, object]]) -> None:
    filename = "bch_decode_time_comparison.png"; data: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(9.0, 5.4))
    try:
        for case in ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300"]:
            rows = sorted((row for row in formal if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
            x = [float(row["ebn0Db"]) for row in rows]; y = [float(row["avgDecodeTimeUs"]) for row in rows]
            axis.plot(x, y, marker="o", markersize=3, label=case)
            data.extend({"caseName": case, "ebn0Db": a, "avgDecodeTimeUs": b} for a, b in zip(x, y))
        axis.set_title("BCH-16 average software decode time"); axis.set_xlabel("Payload Eb/N0 (dB)")
        axis.set_ylabel("Average decode time (us)"); axis.grid(True, alpha=0.3); axis.legend()
        fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally: plt.close(fig)
    data_name = f"figure_data_{Path(filename).stem}.csv"; write_rows(output / data_name, data)
    manifest.append({"filename": filename, "sourceCsv": "formal_summary.csv", "figureDataCsv": data_name,
                     "sha256": sha(output / filename), "dpi": 240, "xColumn": "ebn0Db", "yColumn": "avgDecodeTimeUs",
                     "logScale": False, "zeroHandlingPolicy": "RAW_LINEAR", "generatedBy": "plot_bch_comparison.py",
                     "matplotlibVersion": matplotlib.__version__})


def save_complexity(complexity: list[dict[str, str]], output: Path, manifest: list[dict[str, object]]) -> None:
    filename = "bch_complexity_comparison.png"; metrics = ["segmentCount", "syndromeCount", "bmIterationCount", "chienSearchLength"]
    data: list[dict[str, object]] = []
    fig, axis = plt.subplots(figsize=(9.0, 5.4))
    try:
        x = list(range(len(complexity))); width = 0.8 / len(metrics)
        for index, metric in enumerate(metrics):
            values = [float(row[metric]) if row[metric] else 0.0 for row in complexity]
            axis.bar([value + index * width for value in x], values, width=width, label=metric)
            data.extend({"caseName": row["caseName"], "metric": metric, "value": value} for row, value in zip(complexity, values))
        axis.set_xticks([value + width * 1.5 for value in x], [row["caseName"] for row in complexity])
        axis.set_title("BCH-16 theoretical decoder structure counts"); axis.set_ylabel("Structural count (not operation-equivalent)")
        axis.grid(True, axis="y", alpha=0.3); axis.legend(); fig.savefig(output / filename, dpi=240, bbox_inches="tight")
    finally: plt.close(fig)
    data_name = f"figure_data_{Path(filename).stem}.csv"; write_rows(output / data_name, data)
    manifest.append({"filename": filename, "sourceCsv": "complexity_comparison.csv", "figureDataCsv": data_name,
                     "sha256": sha(output / filename), "dpi": 240, "xColumn": "caseName", "yColumn": "value",
                     "logScale": False, "zeroHandlingPolicy": "MISSING_DIMENSION_SHOWN_AS_ZERO",
                     "generatedBy": "plot_bch_comparison.py", "matplotlibVersion": matplotlib.__version__})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-summary", type=Path, required=True)
    parser.add_argument("--complexity", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    formal, complexity = read_rows(args.formal_summary), read_rows(args.complexity)
    manifest: list[dict[str, object]] = []
    save_performance(formal, 200, args.output_dir, manifest); save_performance(formal, 300, args.output_dir, manifest)
    save_timing(formal, args.output_dir, manifest); save_complexity(complexity, args.output_dir, manifest)
    (args.output_dir / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    forbidden = [path for path in args.output_dir.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if forbidden: raise SystemExit("BLOCKED_BCH16_FIGURE_DATA_MISMATCH")
    if len(manifest) != 4: raise SystemExit("BCH-16 plot count mismatch")
    for item in manifest:
        path = args.output_dir / str(item["filename"])
        if path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n": raise SystemExit("invalid BCH-16 PNG")
    print(f"PASS_BCH16_PLOT_AUDIT png=4 matplotlib={matplotlib.__version__}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
