#!/usr/bin/env python3
import csv
import pathlib
import sys


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: merge_grid_shards.py OUTPUT.csv SHARD_DIR...", file=sys.stderr)
        return 2
    output = pathlib.Path(sys.argv[1])
    rows = []
    fieldnames = None
    for directory in map(pathlib.Path, sys.argv[2:]):
        with (directory / "grid_smoke_summary.csv").open(encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fieldnames = fieldnames or reader.fieldnames
            if reader.fieldnames != fieldnames:
                raise RuntimeError("grid shard schema mismatch")
            rows.extend(reader)
    rows.sort(key=lambda r: (r["group"], r["channel"], float(r["esN0Db"]), r["scheme"]))
    keys = [(r["group"], r["channel"], r["esN0Db"], r["scheme"]) for r in rows]
    if len(rows) != 264 or len(set(keys)) != 264:
        raise RuntimeError(f"expected 264 unique rows, got {len(rows)}/{len(set(keys))}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("PASS_S5_GRID_MERGE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
