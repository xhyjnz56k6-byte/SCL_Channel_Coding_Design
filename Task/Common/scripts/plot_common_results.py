#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLOTS = {
    "ber_vs_ebn0.png": ("ber", "BER"),
    "fer_vs_ebn0.png": ("fer", "FER"),
    "success_rate_vs_ebn0.png": ("successRate", "Success rate"),
    "avg_decode_time_vs_ebn0.png": ("avgDecodeTimeUs", "Average decode time (us)"),
    "max_decode_time_vs_ebn0.png": ("maxDecodeTimeUs", "Maximum decode time (us)"),
    "avg_total_time_vs_ebn0.png": ("avgTotalTimeUs", "Average total time (us)"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    with Path(args.input).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"ebN0_dB", *[field for field, _ in PLOTS.values()]}
    if not rows:
        raise SystemExit("empty CSV")
    if not required.issubset(rows[0]):
        raise SystemExit("missing CSV column")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, (field, label) in PLOTS.items():
        figure, axis = plt.subplots(figsize=(5, 3))
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in rows:
            grouped.setdefault((row["caseName"], row.get("decisionMode", "decision")), []).append(row)
        for key, series in grouped.items():
            series.sort(key=lambda row: float(row["ebN0_dB"]))
            axis.plot([float(row["ebN0_dB"]) for row in series], [float(row[field]) for row in series], marker="o", label=" / ".join(key))
        axis.set_xlabel("Eb/N0 (dB)")
        axis.set_ylabel(label)
        axis.grid(True)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / name, dpi=120)
        plt.close(figure)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
