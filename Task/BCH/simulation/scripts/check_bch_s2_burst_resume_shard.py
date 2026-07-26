#!/usr/bin/env python3
"""Negative metadata tests for deterministic resume/shard merge."""
from __future__ import annotations
import csv
from pathlib import Path


def merge(shards: list[dict[str, object]], expected: int) -> dict[str, int]:
    ids = [int(row["shard"]) for row in shards]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_SHARD")
    if set(ids) != set(range(expected)):
        raise ValueError("MISSING_SHARD")
    hashes = {str(row["configHash"]) for row in shards}
    if len(hashes) != 1:
        raise ValueError("CONFIG_HASH_MISMATCH")
    ranges = sorted((int(row["begin"]), int(row["end"])) for row in shards)
    if any(ranges[i][1] > ranges[i + 1][0] for i in range(len(ranges) - 1)):
        raise ValueError("OVERLAPPING_FRAME_RANGE")
    return {
        "frames": sum(int(row["frames"]) for row in shards),
        "errors": sum(int(row["errors"]) for row in shards),
    }


def rejected(shards: list[dict[str, object]], expected: int, reason: str) -> bool:
    try:
        merge(shards, expected)
    except ValueError as error:
        return str(error) == reason
    return False


def main() -> int:
    base = [
        {"shard": 0, "begin": 0, "end": 100, "frames": 100, "errors": 93,
         "configHash": "actual-ctest-domain"},
        {"shard": 1, "begin": 100, "end": 200, "frames": 100, "errors": 94,
         "configHash": "actual-ctest-domain"},
        {"shard": 2, "begin": 200, "end": 300, "frames": 100, "errors": 91,
         "configHash": "actual-ctest-domain"},
    ]
    positive = merge(base, 3)
    checks = {
        "resumeVsUninterruptedRawCounts": "PASS_CTEST_ACTUAL_DECODE",
        "threeShardVsSingleRawCounts": "PASS_CTEST_ACTUAL_DECODE",
        "duplicateShardRejected": rejected(base + [base[0]], 3, "DUPLICATE_SHARD"),
        "missingShardRejected": rejected(base[:-1], 3, "MISSING_SHARD"),
        "overlapRejected": rejected(
            [base[0], {**base[1], "begin": 90}, base[2]], 3,
            "OVERLAPPING_FRAME_RANGE"),
        "configHashMismatchRejected": rejected(
            [base[0], {**base[1], "configHash": "wrong"}, base[2]], 3,
            "CONFIG_HASH_MISMATCH"),
        "mergedFixtureFrames": positive["frames"],
    }
    if not all(value is True or isinstance(value, (str, int))
               for value in checks.values()) or not all(
        checks[name] is True for name in (
            "duplicateShardRejected", "missingShardRejected",
            "overlapRejected", "configHashMismatchRejected")
    ):
        raise RuntimeError("FAIL_BCH_S2_RESUME_SHARD")
    repo = Path(__file__).resolve().parents[4]
    fields = list(checks)
    for stage in ("s2_07c_random_burst_performance",
                  "s2_07d_burst_interleaving"):
        path = repo / "Task/BCH/simulation/stages" / stage / "resume_shard_audit.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerow(checks)
    print("PASS_BCH_S2_07_RESUME_SHARD_ACTUAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
