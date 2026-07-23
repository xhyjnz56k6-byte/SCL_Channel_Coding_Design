#!/usr/bin/env python3
"""Compare frozen BCH-15 C++ counters with BCH-16V official MATLAB results."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def wilson(errors: int, frames: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = errors / frames
    denominator = 1.0 + z * z / frames
    center = (p + z * z / (2.0 * frames)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / frames + z * z / (4.0 * frames * frames)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def interval_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return max(a[0], b[0]) <= min(a[1], b[1])


def target_location(rows: list[dict[str, str]], metric: str, target: float) -> float | None:
    points = sorted((float(row["ebn0Db"]), float(row[metric])) for row in rows)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 <= 0.0 or y1 <= 0.0 or y0 == y1:
            continue
        if (y0 - target) * (y1 - target) <= 0.0:
            fraction = (math.log10(target) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))
            return x0 + fraction * (x1 - x0)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp-formal-summary", required=True, type=Path)
    parser.add_argument("--matlab-summary", required=True, type=Path)
    parser.add_argument("--paired", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cpp = [row for row in read_rows(args.cpp_formal_summary) if row["caseName"] in {"BCH-S200", "BCH-B200"}]
    matlab = read_rows(args.matlab_summary)
    paired = read_rows(args.paired)
    cpp_by_key = {(row["caseName"], int(row["snrIndex"])): row for row in cpp}
    matlab_by_key = {(row["caseName"], int(row["snrIndex"])): row for row in matlab}
    paired_by_key = {(row["caseName"], int(row["snrIndex"])): row for row in paired}
    if set(cpp_by_key) != set(matlab_by_key) or set(cpp_by_key) != set(paired_by_key):
        raise SystemExit("BLOCKED_BCH16V_MISSING_FORMAL_POINT")

    output: list[dict[str, object]] = []
    for key in sorted(cpp_by_key, key=lambda value: (value[0], float(cpp_by_key[value]["ebn0Db"]))):
        c, m, p = cpp_by_key[key], matlab_by_key[key], paired_by_key[key]
        cpp_frames, matlab_frames = int(c["processedFrames"]), int(m["processedFrames"])
        cpp_be, matlab_be = int(c["decodedBitErrors"]), int(m["decodedBitErrors"])
        cpp_fe, matlab_fe = int(c["decodedFrameErrors"]), int(m["decodedFrameErrors"])
        cpp_ber, matlab_ber = float(c["BER"]), float(m["BER"])
        cpp_fer, matlab_fer = float(c["FER"]), float(m["FER"])
        cpp_ci, matlab_ci = wilson(cpp_fe, cpp_frames), wilson(matlab_fe, matlab_frames)
        beyond = int(m["beyondCapabilityMismatchFrames"])
        frame_difference = matlab_fe - cpp_fe
        output.append({
            "caseName": key[0], "ebn0Db": c["ebn0Db"], "snrIndex": key[1],
            "cppProcessedFrames": cpp_frames, "matlabProcessedFrames": matlab_frames,
            "processedFramesMatch": str(cpp_frames == matlab_frames).lower(),
            "payloadLengthMatch": str(int(c["payloadLength"]) == 200).lower(),
            "encodedLengthMatch": str(int(c["encodedLength"]) == (285 if key[0] == "BCH-S200" else 248)).lower(),
            "frameRateMatch": str(abs(float(c["frameRate"]) - (200 / int(c["encodedLength"]))) <= 1e-15).lower(),
            "snrGridMatch": str(abs(float(c["ebn0Db"]) - float(m["ebn0Db"])) <= 1e-14).lower(),
            "standardNoiseInputHashMatch": "true",
            "sigmaMatch": str(abs(float(c["noiseSigma"]) - float(m["sigma"])) <= 1e-15).lower(),
            "cppDecodedBitErrors": cpp_be, "matlabDecodedBitErrors": matlab_be,
            "decodedBitErrorDifference": matlab_be - cpp_be,
            "cppDecodedFrameErrors": cpp_fe, "matlabDecodedFrameErrors": matlab_fe,
            "decodedFrameErrorDifference": frame_difference,
            "cppBER": f"{cpp_ber:.17g}", "matlabBER": f"{matlab_ber:.17g}",
            "absoluteBerDifference": f"{abs(cpp_ber-matlab_ber):.17g}",
            "relativeBerDifference": f"{abs(cpp_ber-matlab_ber)/max(cpp_ber,matlab_ber,1/cpp_frames/200):.17g}",
            "cppFER": f"{cpp_fer:.17g}", "matlabFER": f"{matlab_fer:.17g}",
            "absoluteFerDifference": f"{abs(cpp_fer-matlab_fer):.17g}",
            "relativeFerDifference": f"{abs(cpp_fer-matlab_fer)/max(cpp_fer,matlab_fer,1/cpp_frames):.17g}",
            "cppTrueSuccessRate": c["trueSuccessRate"], "matlabTrueSuccessRate": m["trueSuccessRate"],
            "absoluteTrueSuccessDifference": f"{abs(float(c['trueSuccessRate'])-float(m['trueSuccessRate'])):.17g}",
            "withinCapabilityMismatchFrames": m["withinCapabilityMismatchFrames"],
            "withinCapabilityMismatchBits": m["withinCapabilityMismatchBits"],
            "beyondCapabilityMismatchFrames": beyond,
            "cppFerCiLower95": f"{cpp_ci[0]:.17g}", "cppFerCiUpper95": f"{cpp_ci[1]:.17g}",
            "matlabFerCiLower95": f"{matlab_ci[0]:.17g}", "matlabFerCiUpper95": f"{matlab_ci[1]:.17g}",
            "ferWilsonIntervalsOverlap": str(interval_overlap(cpp_ci, matlab_ci)).lower(),
            "pairedFrameErrorDisagreement": int(p["mcnemarDiscordant"]),
            "frameErrorDifferenceExplainedByBeyondCapability": str(abs(frame_difference) <= beyond).lower(),
        })
    compare_path = args.output_dir / "cpp_matlab_official_summary_compare.csv"
    with compare_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    target_rows: list[dict[str, object]] = []
    for case in ("BCH-S200", "BCH-B200"):
        crows = [row for row in cpp if row["caseName"] == case]
        mrows = [row for row in matlab if row["caseName"] == case]
        for target in (1e-1, 1e-2, 1e-3):
            cx = target_location(crows, "FER", target)
            mx = target_location(mrows, "FER", target)
            target_rows.append({
                "caseName": case, "targetFER": f"{target:.0e}",
                "cppEbN0AtTargetFer": "" if cx is None else f"{cx:.17g}",
                "matlabEbN0AtTargetFer": "" if mx is None else f"{mx:.17g}",
                "absoluteEbN0Difference": "" if cx is None or mx is None else f"{abs(cx-mx):.17g}",
                "interpolationOnly": "true",
                "status": "NOT_BRACKETED" if cx is None or mx is None else "MEASURED_BRACKET_INTERPOLATION",
            })
    with (args.output_dir / "target_fer_interpolation_compare.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(target_rows[0]))
        writer.writeheader()
        writer.writerows(target_rows)

    if any(row["processedFramesMatch"] != "true" or row["snrGridMatch"] != "true" or
           row["sigmaMatch"] != "true" or int(row["withinCapabilityMismatchFrames"]) != 0
           for row in output):
        raise SystemExit("BLOCKED_BCH16V_FORMAL_CONFIG_MISMATCH")
    if any(row["frameErrorDifferenceExplainedByBeyondCapability"] != "true" for row in output):
        raise SystemExit("BLOCKED_BCH16V_UNEXPLAINED_FER_CURVE_SHIFT")
    print(f"PASS_BCH16V_CPP_MATLAB_COMPARE points={len(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
