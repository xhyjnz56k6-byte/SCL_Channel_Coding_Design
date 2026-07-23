#!/usr/bin/env python3
"""Create the four frozen BCH-16V PNG comparisons with auditable figure data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


PLOTS = [
    ("BCH-S200", "BER", "bch_s200_cpp_vs_matlab_ber.png", "#1f77b4"),
    ("BCH-S200", "FER", "bch_s200_cpp_vs_matlab_fer.png", "#1f77b4"),
    ("BCH-B200", "BER", "bch_b200_cpp_vs_matlab_ber.png", "#ff7f0e"),
    ("BCH-B200", "FER", "bch_b200_cpp_vs_matlab_fer.png", "#ff7f0e"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", required=True, type=Path)
    parser.add_argument("--cpp-source", required=True, type=Path)
    parser.add_argument("--matlab-source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.compare.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    manifest: list[dict[str, object]] = []
    for case, metric, filename, color in PLOTS:
        selected = sorted((row for row in rows if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
        frame_data: list[dict[str, object]] = []
        cpp_column, matlab_column = f"cpp{metric}", f"matlab{metric}"
        for row in selected:
            frames = int(row["cppProcessedFrames"])
            cpp = float(row[cpp_column])
            matlab = float(row[matlab_column])
            frame_data.append({
                "caseName": case, "ebn0Db": row["ebn0Db"], "processedFrames": frames,
                f"cpp{metric}Raw": f"{cpp:.17g}", f"matlab{metric}Raw": f"{matlab:.17g}",
                f"cpp{metric}Plot": f"{cpp if cpp > 0 else 0.5/(frames*(200 if metric=='BER' else 1)):.17g}",
                f"matlab{metric}Plot": f"{matlab if matlab > 0 else 0.5/(frames*(200 if metric=='BER' else 1)):.17g}",
                "cppZeroObserved": str(cpp == 0).lower(), "matlabZeroObserved": str(matlab == 0).lower(),
            })
        data_name = f"figure_data_{Path(filename).stem}.csv"
        data_path = args.output_dir / data_name
        with data_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(frame_data[0]))
            writer.writeheader()
            writer.writerows(frame_data)
        x = [float(row["ebn0Db"]) for row in frame_data]
        cpp_y = [float(row[f"cpp{metric}Plot"]) for row in frame_data]
        matlab_y = [float(row[f"matlab{metric}Plot"]) for row in frame_data]
        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        ax.semilogy(x, cpp_y, color=color, linestyle="-", marker="o", label=f"C++ {case} {metric}")
        ax.semilogy(x, matlab_y, color=color, linestyle="--", marker="s", label=f"MATLAB Official {case} {metric}")
        ax.set_xlabel("Payload Eb/N0 (dB)")
        ax.set_ylabel(metric)
        ax.set_title(f"{case} {metric}: C++ vs MATLAB Official")
        ax.grid(True, which="both", linestyle=":", alpha=0.65)
        ax.legend()
        fig.tight_layout()
        output = args.output_dir / filename
        fig.savefig(output, dpi=240)
        plt.close(fig)
        manifest.append({
            "filename": filename,
            "sourceCppCsv": args.cpp_source.as_posix(),
            "sourceMatlabCsv": args.matlab_source.as_posix(),
            "sourceCompareCsv": args.compare.as_posix(),
            "figureDataCsv": data_name,
            "sha256": sha256(output),
            "dpi": 240,
            "xColumn": "ebn0Db",
            "yColumn": metric,
            "lineStyles": {"cpp": "solid", "matlabOfficial": "dashed"},
            "markers": {"cpp": "circle", "matlabOfficial": "square"},
            "matplotlibVersion": matplotlib.__version__,
            "zeroHandlingPolicy": "Jeffreys-style plotting position 0.5/n; raw zero retained and marked in figure data",
        })
    (args.output_dir / "plot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    forbidden = [path for path in args.output_dir.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if forbidden:
        raise SystemExit("BLOCKED_BCH16V_NON_PNG_PLOT_ARTIFACT")
    print("PASS_BCH16V_PLOTS pngCount=4 nonPngPlotArtifactCount=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
