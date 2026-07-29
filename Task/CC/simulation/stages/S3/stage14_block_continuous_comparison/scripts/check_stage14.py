#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    path = stage / "results" / "stage14_block_continuous_results.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 8:
        raise RuntimeError(f"expected 8 rate/scheme rows, got {len(rows)}")
    by_rate: dict[str, list[dict[str, str]]] = defaultdict(list)
    expected_slots = {
        "A_BLOCK_300": (300, 1, 0),
        "B_CONT_50x6": (50, 6, 30),
        "C_CONT_100x3": (100, 3, 12),
        "D_CONT_150x2": (150, 2, 6),
    }
    for row in rows:
        by_rate[row["rateCase"]].append(row)
        scheme = row["scheme"]
        if scheme not in expected_slots:
            raise RuntimeError(f"unexpected scheme {scheme}")
        slot_bits, slot_count, avoided = expected_slots[scheme]
        if int(row["slotBits"]) != slot_bits or int(row["slotCount"]) != slot_count:
            raise RuntimeError(f"slot definition mismatch for {scheme}")
        if int(row["repeatedTailBitsAvoided"]) != avoided:
            raise RuntimeError(f"tail accounting mismatch for {scheme}")
        if int(row["tailOverheadBits"]) != 6:
            raise RuntimeError("final tail accounting mismatch")
        transmitted = int(row["transmittedBits"])
        expected_transmitted = 612 if row["rateCase"] == "R12" else 459
        if transmitted != expected_transmitted:
            raise RuntimeError("transmitted length mismatch")
        frames = int(row["frames"])
        bit_errors = int(row["bitErrors"])
        frame_errors = int(row["frameErrors"])
        if frames != 1000:
            raise RuntimeError("unexpected frame count")
        if not math.isclose(float(row["BER"]), bit_errors / (300 * frames), rel_tol=1e-12):
            raise RuntimeError("BER formula mismatch")
        if not math.isclose(float(row["FER"]), frame_errors / frames, rel_tol=1e-12):
            raise RuntimeError("FER formula mismatch")
        actual_rate = 300 / transmitted
        if not math.isclose(float(row["normalizedGoodput"]), actual_rate * (1 - float(row["FER"])), rel_tol=1e-12):
            raise RuntimeError("normalized goodput formula mismatch")
        for key in (
            "firstOutputDelaySymbols", "avgDecisionDelaySymbols", "p95DecisionDelaySymbols",
            "maxDecisionDelaySymbols", "fullFrameCompletionSymbols", "avgDecodeTimeUs",
            "p95DecodeTimeUs", "maxDecodeTimeUs", "normalizedGoodput",
        ):
            if not math.isfinite(float(row[key])):
                raise RuntimeError(f"non-finite {key}")
        if scheme.startswith("A_"):
            if int(row["boundaryBits"]) != 0 or int(row["windowBufferBytes"]) != 0:
                raise RuntimeError("block scheme should not have internal boundaries/window buffer")
        else:
            if int(row["boundaryBits"]) <= 0 or int(row["windowBufferBytes"]) <= 0:
                raise RuntimeError("continuous scheme missing boundary/window evidence")
    if set(by_rate) != {"R12", "R23"} or any(len(items) != 4 for items in by_rate.values()):
        raise RuntimeError("rate/scheme matrix incomplete")
    for rate, items in by_rate.items():
        digests = {row["scheme"]: row["schemeExecutionDigest"] for row in items}
        if len(set(digests.values())) != 4:
            raise RuntimeError(f"execution digests are not scheme-specific for {rate}")
    boundary = stage / "results" / "stage14_boundary_relative_offsets.csv"
    with boundary.open(encoding="utf-8", newline="") as handle:
        rel_rows = list(csv.DictReader(handle))
    if not rel_rows:
        raise RuntimeError("missing boundary relative-offset table")
    offsets = {int(row["relativeOffset"]) for row in rel_rows}
    if offsets != set(range(-10, 10)):
        raise RuntimeError("relative boundary offsets incomplete")
    print("PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
