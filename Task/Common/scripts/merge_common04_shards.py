#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


COUNT_FIELDS = ["processedFrames", "totalPayloadBits", "bitErrors", "frameErrors", "successfulFrames"]
IDENTITY_FIELDS = ["schemaVersion", "experimentId", "stage", "codeType", "caseName", "payloadLength", "encodedLength", "ebN0_dB", "snrIndex", "framePoolId", "noisePoolId", "configHash"]
RANGE_FIELDS = ["shardIndex", "frameStart", "frameCount"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    rows: list[dict[str, str]] = []
    for name in args.inputs:
        with Path(name).open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise SystemExit("empty shard input")
    required = set(IDENTITY_FIELDS + RANGE_FIELDS + COUNT_FIELDS)
    if not required.issubset(rows[0]):
        raise SystemExit("shard CSV missing identity or range fields")
    first = {key: rows[0][key] for key in IDENTITY_FIELDS}
    seen_indices: set[int] = set()
    normalized: list[tuple[int, int, dict[str, str]]] = []
    for row in rows:
        if any(row[key] != first[key] for key in IDENTITY_FIELDS):
            raise SystemExit("shard config mismatch")
        shard_index, start, count = int(row["shardIndex"]), int(row["frameStart"]), int(row["frameCount"])
        if count <= 0 or shard_index in seen_indices:
            raise SystemExit("invalid or duplicate shard range")
        seen_indices.add(shard_index)
        if int(row["processedFrames"]) != count or int(row["totalPayloadBits"]) != count * int(row["payloadLength"]) or int(row["successfulFrames"]) + int(row["frameErrors"]) != count:
            raise SystemExit("shard metrics contradict range")
        normalized.append((start, count, row))
    normalized.sort(key=lambda item: item[0])
    expected = normalized[0][0]
    for start, count, _ in normalized:
        if start != expected:
            raise SystemExit("shard frame ranges contain gap or overlap")
        expected += count
    totals = {key: sum(int(row[key]) for _, _, row in normalized) for key in COUNT_FIELDS}
    out = dict(normalized[0][2])
    out.update({key: str(value) for key, value in totals.items()})
    out["frameStart"] = str(normalized[0][0])
    out["frameCount"] = str(sum(count for _, count, _ in normalized))
    out["ber"] = str(totals["bitErrors"] / totals["totalPayloadBits"])
    out["fer"] = str(totals["frameErrors"] / totals["processedFrames"])
    out["successRate"] = str(totals["successfulFrames"] / totals["processedFrames"])
    with Path(args.output).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out.keys()))
        writer.writeheader()
        writer.writerow(out)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
