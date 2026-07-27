#!/usr/bin/env python3
"""Verify every stage08 PNG, figure-data CSV and plot manifest."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
from pathlib import Path

PREFIX = "stage08_multipath_formal"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"BLOCKED_STAGE08_PLOT_CHECK:{message}")


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    index = json.loads((stage / f"{PREFIX}_plot_manifest.json").read_text(encoding="utf-8"))
    require(len(index["plots"]) == 8, "plot count")
    source_rows = {
        f"{row['caseId']}:{row['ebn0Index']}": row
        for row in read(stage / f"results/{PREFIX}_results.csv")
    }
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
        require(manifest["yScale"] in ("log", "linear"), "scale")
        require(sha(png) == manifest["plotFileSha256"], "png hash")
        require(sha(figure) == manifest["figureDataSha256"], "figure hash")
        require(
            sha(stage / manifest["sourceCsv"]) == manifest["sourceCsvSha256"],
            "source hash",
        )
        figure_rows = read(figure)
        require(len(figure_rows) == 12, "figure row count")
        for row in figure_rows:
            source = source_rows[row["sourceRowId"]]
            raw = float(row["rawY"])
            require(math.isfinite(raw) and math.isfinite(float(row["plotY"])), "finite")
            field = manifest["ySourceColumn"]
            require(abs(raw - float(source[field])) <= 1e-12 * max(1.0, abs(raw)), "rawY")
            if row["isZeroObserved"] == "true":
                require(raw == 0.0 and row["plotSurrogateUsed"] == "true", "zero handling")
            else:
                require(row["plotSurrogateUsed"] == "false", "unexpected surrogate")
        require(len(manifest["legendMapping"]) == 4, "legend uniqueness")
        require(len(set(manifest["legendMapping"].values())) == 4, "legend duplicate")
        styles = [entry["styleId"] for entry in manifest["styleMapping"].values()]
        require(len(set(styles)) == 4, "style duplicate")
    forbidden = [
        path for path in stage.rglob("*")
        if path.is_file() and path.suffix.lower() in (".pdf", ".svg", ".eps", ".jpg", ".jpeg")
    ]
    require(not forbidden, "forbidden image format")
    log = stage / f"logs/{PREFIX}_plot_check.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text("PASS_STAGE08_PLOT_CHECK\n", encoding="utf-8")
    print("PASS_STAGE08_PLOT_CHECK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
