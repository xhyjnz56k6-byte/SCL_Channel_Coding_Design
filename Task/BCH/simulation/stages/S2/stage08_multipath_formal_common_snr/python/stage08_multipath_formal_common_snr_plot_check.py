#!/usr/bin/env python3
"""Verify common-SNR PNGs, figure-data CSVs, and plot manifests."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"BLOCKED_STAGE08_COMMON_SNR_PLOT_CHECK:{message}")


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    index = json.loads((stage / f"{PREFIX}_plot_manifest.json").read_text(encoding="utf-8"))
    require(len(index["plots"]) == 8, "plot count")
    source_rows = {f"{row['caseId']}:{row['waveformSnrIndex']}": row for row in read(stage / f"results/{PREFIX}_results.csv")}
    for relative in index["plots"]:
        manifest_path = stage / relative
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        png = stage / manifest["plotFile"]
        figure = stage / manifest["figureDataCsv"]
        require(png.is_file() and png.stat().st_size > 0, "empty png")
        data = png.read_bytes()
        require(data[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature")
        width, height = struct.unpack(">II", data[16:24])
        require(width == manifest["imageWidth"] and height == manifest["imageHeight"], "dimensions")
        require(manifest["imageFormat"] == "PNG", "format")
        require(manifest["xLabel"] == "SNR (dB)", "x label")
        require(manifest["xSourceColumn"] == "waveformSnrDb", "x source")
        require(manifest["gridDefinition"] == "0:0.5:18 dB; BASE_0P5DB; NO_REFINEMENT", "grid definition")
        require(manifest["yScale"] in ("log", "linear"), "scale")
        require(sha(png) == manifest["plotFileSha256"], "png hash")
        require(sha(figure) == manifest["figureDataSha256"], "figure hash")
        require(sha(stage / manifest["sourceCsv"]) == manifest["sourceCsvSha256"], "source hash")
        figure_rows = read(figure)
        require(len(figure_rows) == 148, "figure row count")
        by_case: dict[str, list[dict[str, str]]] = {}
        for row in figure_rows:
            by_case.setdefault(row["caseId"], []).append(row)
            source = source_rows[row["sourceRowId"]]
            raw = float(row["rawY"])
            plot_y = float(row["plotY"])
            require(math.isfinite(raw) and math.isfinite(plot_y), "finite")
            field = manifest["ySourceColumn"]
            require(abs(raw - float(source[field])) <= 1e-12 * max(1.0, abs(raw)), "rawY")
            require(row["waveformSnrDb"] == source["waveformSnrDb"], "x data")
            if row["isZeroObserved"] == "true":
                require(raw == 0.0 and row["plotSurrogateUsed"] == "true", "zero handling")
                count = int(source["totalPayloadBits"]) if field == "ber" else int(source["totalFrames"])
                require(abs(plot_y - 0.5 / count) <= 1e-18, "surrogate formula")
            else:
                require(row["plotSurrogateUsed"] == "false", "unexpected surrogate")
        require(len(by_case) == 4, "case count")
        for case_rows in by_case.values():
            xs = sorted(float(row["waveformSnrDb"]) for row in case_rows)
            require(xs == [i * 0.5 for i in range(37)], "37 point x coverage")
        require(len(manifest["legendMapping"]) == 4, "legend uniqueness")
        require(len(set(manifest["legendMapping"].values())) == 4, "legend duplicate")
        styles = [entry["styleId"] for entry in manifest["styleMapping"].values()]
        require(len(set(styles)) == 4, "style duplicate")
        (manifest_path.parent / manifest_path.name.replace("_plot_manifest.json", "_plot_check.log")).write_text(
            f"PASS_STAGE08_COMMON_SNR_PLOT_CHECK plot={manifest['plotFile']}\n",
            encoding="utf-8",
        )
    forbidden = [path for path in stage.rglob("*") if path.is_file() and path.suffix.lower() in (".pdf", ".svg", ".eps", ".jpg", ".jpeg")]
    require(not forbidden, "forbidden image format")
    log = stage / f"logs/{PREFIX}_plot_check.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text("PASS_STAGE08_COMMON_SNR_PLOT_CHECK\n", encoding="utf-8")
    print("PASS_STAGE08_COMMON_SNR_PLOT_CHECK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
