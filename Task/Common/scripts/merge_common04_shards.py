#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


COUNT_FIELDS = ["processedFrames", "totalPayloadBits", "bitErrors", "frameErrors", "successfulFrames"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    rows = []
    for name in args.inputs:
        with Path(name).open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise SystemExit("empty shard input")
    base_keys = ["schemaVersion", "experimentId", "stage", "codeType", "caseName", "payloadLength", "encodedLength", "ebN0_dB", "snrIndex", "framePoolId", "noisePoolId", "configHash"]
    first = {key: rows[0][key] for key in base_keys}
    totals = {key: 0 for key in COUNT_FIELDS}
    for row in rows:
        for key in base_keys:
            if row[key] != first[key]:
                raise SystemExit(f"shard config mismatch: {key}")
        for key in COUNT_FIELDS:
            totals[key] += int(row[key])
    out = dict(rows[0])
    out.update({key: str(value) for key, value in totals.items()})
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
