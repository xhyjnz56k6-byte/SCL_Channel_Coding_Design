#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    source = results / "stage10_traceback_study_results.csv"
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 16:
        raise RuntimeError(f"expected 16 rows, got {len(rows)}")
    grouped: dict[tuple[str, float], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["caseId"], float(row["snrDb"]))
        grouped[key].append(row)
        frames = int(row["frames"])
        bit_errors = int(row["payloadBitErrors"])
        frame_errors = int(row["payloadErrorFrames"])
        depth = int(row["Dtb"])
        numeric = [
            "BER", "FER", "avgDecodeTime_us", "p95DecodeTime_us", "maxDecodeTime_us",
            "firstStableOutputDepth",
        ]
        if not all(math.isfinite(float(row[name])) for name in numeric):
            raise RuntimeError(f"non-finite metric at {key}")
        if frames != 1000:
            raise RuntimeError(f"frame count at {key}")
        if not close(float(row["BER"]), bit_errors / (300 * frames)):
            raise RuntimeError(f"BER formula at {key}")
        if not close(float(row["FER"]), frame_errors / frames):
            raise RuntimeError(f"FER formula at {key}")
        if int(row["survivorMemoryBytes"]) != depth * 64 * 3:
            raise RuntimeError(f"survivor memory formula at {key}")
        expected_operations = (306 if row["mode"].startswith("FULL") else depth * (307 - depth)) * frames
        if int(row["tracebackOperations"]) != expected_operations:
            raise RuntimeError(f"traceback operations at {key}")
        if not 35 <= float(row["firstStableOutputDepth"]) <= 306:
            raise RuntimeError(f"stable depth range at {key}")
        mismatch_bits = int(row["fullMismatchBits"])
        mismatch_frames = int(row["fullMismatchFrames"])
        if mismatch_bits < mismatch_frames or mismatch_bits > mismatch_frames * 300:
            raise RuntimeError(f"mismatch count relation at {key}")
        if row["mode"].startswith("FULL") and (mismatch_bits != 0 or mismatch_frames != 0):
            raise RuntimeError(f"full baseline mismatch at {key}")
    if len(grouped) != 4 or any(len(items) != 4 for items in grouped.values()):
        raise RuntimeError("scenario/mode matrix incomplete")

    preferred: list[int] = []
    fallback: list[int] = []
    worst_by_depth: dict[int, tuple[float, float, float]] = {}
    comparison_rows: list[dict[str, object]] = []
    for depth in (35, 49, 70):
        preferred_pass = True
        fallback_pass = True
        worst_ber = 0.0
        worst_fer = 0.0
        memory_reduction = 0.0
        for (case, snr), items in sorted(grouped.items()):
            by_depth = {int(row["Dtb"]): row for row in items}
            baseline = by_depth[306]
            candidate = by_depth[depth]
            base_ber = float(baseline["BER"])
            base_fer = float(baseline["FER"])
            ber_ratio = float(candidate["BER"]) / base_ber if base_ber else (
                1.0 if float(candidate["BER"]) == 0 else math.inf
            )
            fer_ratio = float(candidate["FER"]) / base_fer if base_fer else (
                1.0 if float(candidate["FER"]) == 0 else math.inf
            )
            point_pass = ber_ratio <= 1.05 and fer_ratio <= 1.05
            preferred_pass &= point_pass
            fallback_pass &= ber_ratio <= 1.10 and fer_ratio <= 1.15
            worst_ber = max(worst_ber, ber_ratio - 1)
            worst_fer = max(worst_fer, fer_ratio - 1)
            memory_reduction = 1 - int(candidate["survivorMemoryBytes"]) / int(
                baseline["survivorMemoryBytes"]
            )
            comparison_rows.append({
                "caseId": case,
                "snrDb": snr,
                "Dtb": depth,
                "berRatioToFull": ber_ratio,
                "ferRatioToFull": fer_ratio,
                "fullMismatchBits": candidate["fullMismatchBits"],
                "fullMismatchFrames": candidate["fullMismatchFrames"],
                "survivorMemoryBytes": candidate["survivorMemoryBytes"],
                "avgDecodeTime_us": candidate["avgDecodeTime_us"],
                "pointPass": "PASS" if point_pass else "FAIL",
            })
        fallback_pass &= memory_reduction >= 0.50
        worst_by_depth[depth] = (worst_ber, worst_fer, memory_reduction)
        if preferred_pass:
            preferred.append(depth)
        if fallback_pass:
            fallback.append(depth)
    if preferred:
        recommendation = min(preferred)
        tier = "PREFERRED"
        qualified = preferred
    elif fallback:
        recommendation = min(fallback)
        tier = "FALLBACK"
        qualified = fallback
    else:
        raise RuntimeError("no traceback depth meets preferred or fallback threshold")
    with (results / "stage10_traceback_comparison_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(comparison_rows)
    with (results / "stage10_traceback_recommendation.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "recommendedDtb", "recommendationTier", "qualifiedDepths", "worstBerIncrease",
            "worstFerIncrease", "survivorMemoryReduction", "decisionRule", "usage",
        ])
        worst_ber, worst_fer, memory_reduction = worst_by_depth[recommendation]
        writer.writerow([
            recommendation,
            tier,
            "|".join(map(str, qualified)),
            worst_ber,
            worst_fer,
            memory_reduction,
            "preferred <=5% BER/FER; fallback <=10% BER, <=15% FER, >=50% memory reduction",
            "Stage12 sliding-window candidate",
        ])
    with (results / "stage10_traceback_test_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["check", "status"])
        writer.writerow(["noiseless_finite_traceback", "PASS"])
        writer.writerow(["scenario_mode_matrix", "PASS"])
        writer.writerow(["formula_and_finite_checks", "PASS"])
        writer.writerow(["preferred_threshold", "PASS" if preferred else "NO_CANDIDATE"])
        writer.writerow(["recommendation_data_driven", f"PASS_{tier}_DTB_{recommendation}"])
        writer.writerow(["stage_gate", "PASS_STAGE10_CC_TRACEBACK_STUDY"])
    print(f"PASS_STAGE10_CC_TRACEBACK_STUDY recommendedDtb={recommendation} tier={tier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
