#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    with (results / "stage13_sliding_window_results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 21:
        raise RuntimeError(f"expected 21 scenario/config rows, got {len(rows)}")
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_configs: set[tuple[int, int, int]] = set()
    for row in rows:
        groups[row["caseId"]].append(row)
        cfg = (
            int(row["windowInputBits"]),
            int(row["slideStepBits"]),
            int(row["tracebackDepthBits"]),
        )
        seen_configs.add(cfg)
        if cfg[1] > cfg[0] or cfg[2] > cfg[0]:
            raise RuntimeError(f"invalid W/S/D relationship: {cfg}")
        for key in (
            "BER", "FER", "avgDecisionDelaySymbols", "p95DecisionDelaySymbols",
            "maxDecisionDelaySymbols", "avgDecodeTimeUs", "p95DecodeTimeUs",
            "maxDecodeTimeUs",
        ):
            if not math.isfinite(float(row[key])):
                raise RuntimeError(f"non-finite {key}")
        frames = int(row["frames"])
        bit_errors = int(row["bitErrors"])
        frame_errors = int(row["frameErrors"])
        if frames != 1000:
            raise RuntimeError("unexpected frame count")
        if not math.isclose(float(row["BER"]), bit_errors / (300 * frames), rel_tol=1e-12):
            raise RuntimeError("BER formula mismatch")
        if not math.isclose(float(row["FER"]), frame_errors / frames, rel_tol=1e-12):
            raise RuntimeError("FER formula mismatch")
        if int(row["firstOutputDelaySymbols"]) != cfg[0] - 1:
            raise RuntimeError("window not reflected in first-output delay")
        if int(row["survivorMemoryBytes"]) != cfg[0] * 64 * 3:
            raise RuntimeError("window not reflected in survivor memory")
        if int(row["windowBufferBytes"]) != cfg[0] * 2 * 8:
            raise RuntimeError("window buffer formula mismatch")
        mismatch_parts = sum(int(row[key]) for key in (
            "headMismatchBits", "boundaryMismatchBits", "middleMismatchBits", "tailMismatchBits"
        ))
        if mismatch_parts != int(row["fullMismatchBits"]):
            raise RuntimeError("mismatch region partition failed")
    if len(groups) != 3 or any(len(items) != 7 for items in groups.values()):
        raise RuntimeError("scenario/config matrix incomplete")
    if len(seen_configs) != 7:
        raise RuntimeError("config sweep collapsed")
    with (results / "stage13_output_bit_metadata.csv").open(encoding="utf-8", newline="") as handle:
        meta = list(csv.DictReader(handle))
    meta_groups: dict[tuple[int, int, int], list[dict[str, str]]] = defaultdict(list)
    for row in meta:
        meta_groups[(
            int(row["windowInputBits"]),
            int(row["slideStepBits"]),
            int(row["tracebackDepthBits"]),
        )].append(row)
    if set(meta_groups) != seen_configs:
        raise RuntimeError("metadata config coverage mismatch")
    for cfg, items in meta_groups.items():
        indexes = [int(row["bitIndex"]) for row in items]
        if indexes != list(range(300)):
            raise RuntimeError(f"metadata bit coverage failed: {cfg}")
        if any(int(row["decisionTimeInputBit"]) < int(row["receiveTimeInputBit"]) for row in items):
            raise RuntimeError(f"decision before receive: {cfg}")
    print("PASS_STAGE13_CC_SLIDING_WINDOW")
    return 0


if __name__ == "__main__":
    sys.exit(main())
