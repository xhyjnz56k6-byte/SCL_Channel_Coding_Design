#!/usr/bin/env python3
"""Build the BCH-16 segmented-versus-block comparison without extrapolation."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


TARGETS = [1e-1, 1e-2, 1e-3]
PAIRS = {200: ("BCH-S200", "BCH-B200"), 300: ("BCH-S300", "BCH-B300")}
CASE_CONFIG = {
    "BCH-S200": (200, 285, "SYNDROME_LOOKUP", "19 shortened BCH(15,11) segments"),
    "BCH-B200": (200, 248, "BERLEKAMP_MASSEY_CHIEN", "shortened BCH(255,207), t=6"),
    "BCH-S300": (300, 420, "SYNDROME_LOOKUP", "28 shortened BCH(15,11) segments"),
    "BCH-B300": (300, 390, "BERLEKAMP_MASSEY_CHIEN", "shortened BCH(511,421), t=10"),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def interpolate(rows: list[dict[str, str]], target: float) -> tuple[float | None, dict[str, object]]:
    ordered = sorted(rows, key=lambda row: float(row["ebn0Db"]))
    exact = [row for row in ordered if math.isclose(float(row["FER"]), target, rel_tol=0.0, abs_tol=1e-15)]
    if exact:
        value = float(exact[0]["ebn0Db"])
        point = f"EbN0={value:.6g};FER={target:.12g}"
        return value, {"lowerPoint": point, "upperPoint": point, "interpolatedEbN0": value,
                       "interpolationValid": "true", "reason": "EXACT_OBSERVATION"}
    for left, right in zip(ordered, ordered[1:]):
        left_fer, right_fer = float(left["FER"]), float(right["FER"])
        if left_fer <= 0.0 or right_fer <= 0.0:
            continue
        if (left_fer - target) * (right_fer - target) < 0.0:
            left_x, right_x = float(left["ebn0Db"]), float(right["ebn0Db"])
            fraction = (math.log10(target) - math.log10(left_fer)) / (math.log10(right_fer) - math.log10(left_fer))
            value = left_x + fraction * (right_x - left_x)
            return value, {
                "lowerPoint": f"EbN0={left_x:.6g};FER={left_fer:.12g}",
                "upperPoint": f"EbN0={right_x:.6g};FER={right_fer:.12g}",
                "interpolatedEbN0": value, "interpolationValid": "true",
                "reason": "LOG10_FER_LINEAR_INTERPOLATION",
            }
    return None, {"lowerPoint": "", "upperPoint": "", "interpolatedEbN0": "",
                  "interpolationValid": "false", "reason": "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.formal_summary)
    expected = {(case, float(row["ebn0Db"])) for case in CASE_CONFIG for row in rows if row["caseName"] == case}
    if len(rows) != 65 or len(expected) != 65 or {row["caseName"] for row in rows} != set(CASE_CONFIG):
        raise SystemExit("BLOCKED_BCH16_COMPARISON_INPUT_INCOMPLETE")

    interpolation_rows: list[dict[str, object]] = []
    interpolated: dict[tuple[str, float], float | None] = {}
    for case in CASE_CONFIG:
        case_rows = [row for row in rows if row["caseName"] == case]
        for target in TARGETS:
            value, audit = interpolate(case_rows, target); interpolated[(case, target)] = value
            interpolation_rows.append({"caseName": case, "targetFer": target, **audit})
    write_rows(args.output_dir / "interpolation_audit.csv", interpolation_rows)

    gain_rows: list[dict[str, object]] = []
    for payload, (segmented, block) in PAIRS.items():
        for target in TARGETS:
            seg_value, block_value = interpolated[(segmented, target)], interpolated[(block, target)]
            valid = seg_value is not None and block_value is not None
            gain_rows.append({"payloadLength": payload, "targetFer": target,
                              "segmentedEbN0": "" if seg_value is None else seg_value,
                              "blockEbN0": "" if block_value is None else block_value,
                              "gainBlockVsSegmented": "" if not valid else seg_value - block_value,
                              "gainValid": str(valid).lower(),
                              "reason": "BOTH_CASES_BRACKET_TARGET" if valid else "AT_LEAST_ONE_CASE_NOT_BRACKETED"})
    write_rows(args.output_dir / "coding_gain_summary.csv", gain_rows)

    comparison_rows: list[dict[str, object]] = []
    for case, (payload, encoded, decoder, structure) in CASE_CONFIG.items():
        case_rows = [row for row in rows if row["caseName"] == case]
        total_frames = sum(int(row["processedFrames"]) for row in case_rows)
        representative = min(case_rows, key=lambda row: abs(math.log10(float(row["FER"])) - math.log10(1e-2)))
        recommendation = ("Prefer for AWGN performance, rate, and compact codeword" if case.startswith("BCH-B") else
                          "Prefer when tiny fixed lookup blocks and regular parallel structure dominate")
        comparison_rows.append({
            "payloadLength": payload, "caseName": case, "encodedLength": encoded,
            "frameRate": payload / encoded, "redundancyBits": encoded - payload,
            "decoderType": decoder, "correctionStructure": structure,
            "EbN0AtFer1e1": "" if interpolated[(case, 1e-1)] is None else interpolated[(case, 1e-1)],
            "EbN0AtFer1e2": "" if interpolated[(case, 1e-2)] is None else interpolated[(case, 1e-2)],
            "EbN0AtFer1e3": "" if interpolated[(case, 1e-3)] is None else interpolated[(case, 1e-3)],
            "avgDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) * int(row["processedFrames"]) for row in case_rows) / total_frames,
            "p95DecodeTimeUs": max(float(row["p95DecodeTimeUs"]) for row in case_rows),
            "p99DecodeTimeUs": max(float(row["p99DecodeTimeUs"]) for row in case_rows),
            "maxDecodeTimeUs": max(float(row["maxDecodeTimeUs"]) for row in case_rows),
            "miscorrectionRateAtRepresentativePoint": representative["miscorrectionRate"],
            "decoderFailureRateAtRepresentativePoint": representative["decoderFailureRate"],
            "representativePointEbN0Db": representative["ebn0Db"],
            "representativePointFer": representative["FER"],
            "complexitySummary": structure, "recommendation": recommendation,
        })
    write_rows(args.output_dir / "comparison_summary.csv", comparison_rows)

    complexity_rows = [
        {"caseName": "BCH-S200", "segmentCount": 19, "syndromeLookupCount": 19, "maxLookupTableSize": 15,
         "perFrameBlockLoops": 19, "syndromeCount": "", "bmIterationCount": "", "chienSearchLength": "", "gfOperationProfile": "table lookup per segment"},
        {"caseName": "BCH-B200", "segmentCount": "", "syndromeLookupCount": "", "maxLookupTableSize": "",
         "perFrameBlockLoops": "", "syndromeCount": 12, "bmIterationCount": 12, "chienSearchLength": 255, "gfOperationProfile": "GF(2^8) BM and Chien"},
        {"caseName": "BCH-S300", "segmentCount": 28, "syndromeLookupCount": 28, "maxLookupTableSize": 15,
         "perFrameBlockLoops": 28, "syndromeCount": "", "bmIterationCount": "", "chienSearchLength": "", "gfOperationProfile": "table lookup per segment"},
        {"caseName": "BCH-B300", "segmentCount": "", "syndromeLookupCount": "", "maxLookupTableSize": "",
         "perFrameBlockLoops": "", "syndromeCount": 20, "bmIterationCount": 20, "chienSearchLength": 511, "gfOperationProfile": "GF(2^9) BM and Chien"},
    ]
    write_rows(args.output_dir / "complexity_comparison.csv", complexity_rows)
    (args.output_dir / "recommendations.md").write_text(
        "# BCH-16 recommendations\n\n"
        "For 200-bit payloads, BCH-B200 is recommended when AWGN FER, shorter encoded length, higher rate, and memory "
        "efficiency dominate; BCH-S200 is recommended when small fixed tables, simple independent blocks, regular "
        "parallel hardware, and substantially lower software decode latency dominate.\n\n"
        "For 300-bit payloads, BCH-B300 is recommended when AWGN FER, shorter encoded length, higher rate, and memory "
        "efficiency dominate; BCH-S300 is recommended when regular segment parallelism, small lookup tables, and lower "
        "software decode latency dominate. Reported-success semantics differ: segmented miscorrrections are visible "
        "while whole-block bounded-distance failures are explicitly reported, so both true success and status metrics "
        "must accompany FER.\n\n"
        "突发错误和交织影响留待 BCH-17。\n", encoding="utf-8")
    print("PASS_BCH16_COMPARISON_TABLES cases=4 interpolationRows=12 gains=6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
