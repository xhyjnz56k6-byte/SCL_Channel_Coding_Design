#!/usr/bin/env python3
"""Merge BCH shard raw counts after strict identity and range validation."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


IDENTITY = ["caseName", "ebn0Db", "payloadLength", "encodedLength", "frameRate", "globalSeed",
            "noisePolicyVersion", "snrIndex", "logicalFrameCount", "shardCount", "configHash"]
COUNTERS = ["processedFrames", "processedPayloadBits", "channelHardBitErrors", "channelHardFrameErrors",
            "decodedBitErrors", "decodedFrameErrors", "trueSuccessFrames", "reportedSuccessFrames",
            "miscorrectedFrames", "decoderFailureFrames", "noErrorStatusFrames", "correctedStatusFrames",
            "failedStatusFrames"]


def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        values = list(csv.DictReader(handle))
    if len(values) != 1: raise ValueError("each shard summary must have exactly one row")
    return values[0]


def merge(inputs: list[Path], expected_start: int, expected_count: int, expected_shards: int) -> dict[str, object]:
    if len(inputs) != expected_shards: raise ValueError("missing shard input")
    values = [read_one(path) for path in inputs]
    first = values[0]
    if any(any(row[field] != first[field] for field in IDENTITY) for row in values[1:]):
        raise ValueError("shard identity or config mismatch")
    indices = [int(row["shardIndex"]) for row in values]
    if len(set(indices)) != len(indices) or sorted(indices) != list(range(expected_shards)):
        raise ValueError("duplicate or missing shard index")
    ranges = sorted((int(row["frameStart"]), int(row["requestedFrameCount"]), row) for row in values)
    cursor = expected_start
    for start, count, row in ranges:
        if start != cursor: raise ValueError("shard frame ranges contain gap or overlap")
        if int(row["processedFrames"]) != count: raise ValueError("shard did not process its fixed range")
        cursor += count
    if cursor != expected_start + expected_count: raise ValueError("shard range does not cover expected frame count")
    merged: dict[str, object] = {field: first[field] for field in IDENTITY}
    merged.update({field: sum(int(row[field]) for row in values) for field in COUNTERS})
    frames = int(merged["processedFrames"]); bits = int(merged["processedPayloadBits"])
    merged.update({"frameStart": expected_start, "requestedFrameCount": expected_count,
                   "BER": int(merged["decodedBitErrors"]) / bits,
                   "FER": int(merged["decodedFrameErrors"]) / frames,
                   "trueSuccessRate": int(merged["trueSuccessFrames"]) / frames,
                   "reportedSuccessRate": int(merged["reportedSuccessFrames"]) / frames,
                   "miscorrectionRate": int(merged["miscorrectedFrames"]) / frames,
                   "decoderFailureRate": int(merged["decoderFailureFrames"]) / frames,
                   "loadedShards": len(values), "duplicateFrames": 0, "missingFrames": 0,
                   "configHashStatus": "PASS", "stopReason": "SHARD_RAW_COUNTS_MERGED"})
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-frame-start", type=int, default=0)
    parser.add_argument("--expected-frame-count", type=int, required=True)
    parser.add_argument("--expected-shard-count", type=int, required=True)
    args = parser.parse_args()
    try:
        row = merge(args.inputs, args.expected_frame_start, args.expected_frame_count, args.expected_shard_count)
    except ValueError as error:
        raise SystemExit(f"BLOCKED_BCH14_SHARD_MERGE_MISMATCH: {error}") from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    print(f"PASS_BCH14_SHARD_MERGE loadedShards={row['loadedShards']} mergedFrames={row['processedFrames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
