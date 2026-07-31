#!/usr/bin/env python3
"""Shard Stage13 plans without splitting a shared-noise rate/SNR group."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("plan output-directory shard-count")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    shard_count = int(sys.argv[3])
    with source.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["rateCase"], row["snrDb"])].append(row)
    shards = [[] for _ in range(shard_count)]
    for index, key in enumerate(sorted(groups)):
        shards[index % shard_count].extend(groups[key])
    output.mkdir(parents=True, exist_ok=True)
    for index, shard in enumerate(shards):
        path = output / f"stage13_plan_shard_{index}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(shard)
    print(
        "PASS_STAGE13_PLAN_SHARD "
        + ",".join(str(len(shard)) for shard in shards)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
