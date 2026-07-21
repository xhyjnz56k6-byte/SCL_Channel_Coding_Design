#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


COUNT_FIELDS = ["processedFrames", "totalPayloadBits", "bitErrors", "frameErrors", "successfulFrames"]
SUM_LATENCY = ["encodeTimeNsSum", "channelTimeNsSum", "decodeTimeNsSum", "recoveryTimeNsSum", "totalTimeNsSum"]
MAX_LATENCY = ["maxDecodeTimeNs", "maxTotalTimeNs"]
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
    required = set(IDENTITY_FIELDS + RANGE_FIELDS + COUNT_FIELDS + SUM_LATENCY + MAX_LATENCY)
    if not required.issubset(rows[0]):
        raise SystemExit("shard CSV missing identity, range, or latency fields")
    first = {key: rows[0][key] for key in IDENTITY_FIELDS}
    seen_indices: set[int] = set()
    normalized: list[tuple[int, int, dict[str, str]]] = []
    for row in rows:
        if not required.issubset(row):
            raise SystemExit("shard CSV field missing")
        if any(row[key] != first[key] for key in IDENTITY_FIELDS):
            raise SystemExit("shard config mismatch")
        try:
            shard_index, start, count = int(row["shardIndex"]), int(row["frameStart"]), int(row["frameCount"])
            values = {key: int(row[key]) for key in COUNT_FIELDS + SUM_LATENCY + MAX_LATENCY}
        except ValueError as error:
            raise SystemExit("shard count or latency is not an integer") from error
        if min(values.values()) < 0 or count <= 0 or shard_index in seen_indices:
            raise SystemExit("invalid or duplicate shard range")
        seen_indices.add(shard_index)
        if values["processedFrames"] != count or values["totalPayloadBits"] != count * int(row["payloadLength"]) or values["successfulFrames"] + values["frameErrors"] != count:
            raise SystemExit("shard metrics contradict range")
        normalized.append((start, count, row))
    normalized.sort(key=lambda item: item[0])
    expected = normalized[0][0]
    for start, count, _ in normalized:
        if start != expected:
            raise SystemExit("shard frame ranges contain gap or overlap")
        expected += count
    totals = {key: sum(int(row[key]) for _, _, row in normalized) for key in COUNT_FIELDS + SUM_LATENCY}
    maxima = {key: max(int(row[key]) for _, _, row in normalized) for key in MAX_LATENCY}
    processed = totals["processedFrames"]
    out = dict(normalized[0][2])
    out.update({key: str(value) for key, value in totals.items()})
    out.update({key: str(value) for key, value in maxima.items()})
    out["frameStart"] = str(normalized[0][0])
    out["frameCount"] = str(sum(count for _, count, _ in normalized))
    out["ber"] = str(totals["bitErrors"] / totals["totalPayloadBits"])
    out["fer"] = str(totals["frameErrors"] / processed)
    out["successRate"] = str(totals["successfulFrames"] / processed)
    for source, target in [("encodeTimeNsSum", "avgEncodeTimeUs"), ("channelTimeNsSum", "avgChannelTimeUs"),
                           ("decodeTimeNsSum", "avgDecodeTimeUs"), ("recoveryTimeNsSum", "avgRecoveryTimeUs"),
                           ("totalTimeNsSum", "avgTotalTimeUs")]:
        out[target] = str(totals[source] / processed / 1000.0)
    out["maxDecodeTimeUs"] = str(maxima["maxDecodeTimeNs"] / 1000.0)
    out["maxTotalTimeUs"] = str(maxima["maxTotalTimeNs"] / 1000.0)
    with Path(args.output).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out.keys()))
        writer.writeheader()
        writer.writerow(out)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
