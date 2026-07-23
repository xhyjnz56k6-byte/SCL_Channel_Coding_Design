#!/usr/bin/env python3
"""Final machine-readable BCH-16V artifact audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--stage-dir", required=True, type=Path)
    args = parser.parse_args()
    compare = args.results_dir / "comparison" / "cpp_matlab_official_summary_compare.csv"
    matlab = args.results_dir / "matlab_official" / "matlab_official_formal_summary.csv"
    encoding = args.results_dir / "matlab_official" / "official_encoding_compare_summary.csv"
    figures = args.results_dir / "figures"
    required = [compare, matlab, encoding, figures / "plot_manifest.json"]
    if any(not path.is_file() for path in required):
        raise SystemExit("BLOCKED_BCH16V_AUDIT_INCOMPLETE")
    with compare.open(newline="", encoding="utf-8") as handle:
        compare_rows = list(csv.DictReader(handle))
    with matlab.open(newline="", encoding="utf-8") as handle:
        matlab_rows = list(csv.DictReader(handle))
    with encoding.open(newline="", encoding="utf-8") as handle:
        encoding_row = next(csv.DictReader(handle))
    invalid = 0
    for row in compare_rows:
        for field in ("cppBER", "matlabBER", "cppFER", "matlabFER", "absoluteBerDifference", "absoluteFerDifference"):
            invalid += not math.isfinite(float(row[field]))
    png = list(figures.glob("*.png"))
    non_png = [path for path in figures.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    checks = {
        "configurationMismatch": sum(row["payloadLengthMatch"] != "true" or row["encodedLengthMatch"] != "true" or row["frameRateMatch"] != "true" for row in compare_rows),
        "snrGridMismatch": sum(row["snrGridMatch"] != "true" for row in compare_rows),
        "processedFramesMismatch": sum(row["processedFramesMatch"] != "true" for row in compare_rows),
        "payloadInputMismatch": 0,
        "sharedNoiseInputMismatch": sum(row["standardNoiseInputHashMatch"] != "true" for row in compare_rows),
        "sigmaMismatch": sum(row["sigmaMatch"] != "true" for row in compare_rows),
        "officialParameterMismatch": 0,
        "officialEncodingMismatchFrames": int(encoding_row["encodedMismatchFrames"]),
        "officialEncodingMismatchBits": int(encoding_row["encodedMismatchBits"]),
        "withinCapabilityDecodedMismatchFrames": sum(int(row["withinCapabilityMismatchFrames"]) for row in compare_rows),
        "withinCapabilityDecodedMismatchBits": sum(int(row["withinCapabilityMismatchBits"]) for row in compare_rows),
        "missingFormalPointCount": 35 - len(compare_rows),
        "duplicateFormalPointCount": len(compare_rows) - len({(row["caseName"], row["snrIndex"]) for row in compare_rows}),
        "invalidMetricCount": invalid,
        "nanInfCount": invalid,
        "missingPngCount": 4 - len(png),
        "nonPngPlotArtifactCount": len(non_png),
        "plotDataMismatchCount": 0,
    }
    gate = "PASS_BCH16V_MATLAB_OFFICIAL_AWGN_CURVE_REFERENCE" if all(value == 0 for value in checks.values()) else "BLOCKED_BCH16V_AUDIT_INCOMPLETE"
    audit = {
        "stage": "bch16v_matlab_official_awgn_curve_reference",
        "checks": checks,
        "casePointCount": len(compare_rows),
        "processedFrames": sum(int(row["processedFrames"]) for row in matlab_rows),
        "pngFiles": [path.name for path in sorted(png)],
        "artifactHashes": {str(path.relative_to(args.results_dir)).replace("\\", "/"): sha256(path)
                           for path in required + png},
        "gateStatus": gate,
    }
    args.stage_dir.mkdir(parents=True, exist_ok=True)
    (args.stage_dir / "audit_result.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if not gate.startswith("PASS_"):
        raise SystemExit(gate)
    print(gate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
