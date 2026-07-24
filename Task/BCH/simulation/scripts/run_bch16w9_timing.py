#!/usr/bin/env python3
"""Rerun BCH16W9 decode timing with warmup and repeated measurements."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import subprocess
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--formal-summary", type=Path, required=True)
    parser.add_argument("--k200-manifest", type=Path, required=True)
    parser.add_argument("--k300-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--warmup-frames", type=int, default=500)
    parser.add_argument("--timed-frames", type=int, default=5000)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise SystemExit(f"BLOCKED_BCH16W9_OUTPUT_ALREADY_EXISTS: {args.output_dir}")
    if args.warmup_frames < 1 or args.timed_frames < 1 or args.repetitions < 3:
        raise SystemExit("BLOCKED_BCH16W9_INVALID_TIMING_PROTOCOL")
    args.output_dir.mkdir(parents=True)

    source = read_rows(args.formal_summary)
    required_cases = {
        "BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"
    }
    actual_cases = {row["caseName"] for row in source}
    if actual_cases != required_cases:
        raise SystemExit(
            f"BLOCKED_BCH16W9_CASE_SET expected={sorted(required_cases)} "
            f"actual={sorted(actual_cases)}"
        )

    repetition_rows: list[dict[str, object]] = []
    total = len(source) * args.repetitions
    completed = 0
    for source_row in source:
        case_name = source_row["caseName"]
        payload_length = int(source_row["payloadLength"])
        manifest = args.k200_manifest if payload_length == 200 else args.k300_manifest
        for repetition in range(1, args.repetitions + 1):
            point_dir = (
                args.output_dir / "raw" / case_name
                / f"point_{int(source_row['snrIndex']):03d}" / f"rep_{repetition}"
            )
            command = [
                str(args.runner),
                "--stage", "BCH16W9_TIMING",
                "--case", case_name,
                "--ebn0-db", source_row["ebn0Db"],
                "--snr-index", source_row["snrIndex"],
                "--frame-start", "0",
                "--frame-count", str(args.timed_frames),
                "--logical-frame-count", str(args.timed_frames),
                "--global-seed", source_row["globalSeed"],
                "--frame-pool-manifest", str(manifest),
                "--output-dir", str(point_dir),
                "--timing-warmup-frames", str(args.warmup_frames),
                "--no-progress",
            ]
            completed += 1
            print(
                f"[{completed}/{total}] {case_name} Eb/N0={source_row['ebn0Db']} "
                f"repeat={repetition}",
                flush=True,
            )
            subprocess.run(command, check=True)
            measured = read_rows(point_dir / "summary.csv")
            if len(measured) != 1:
                raise SystemExit("BLOCKED_BCH16W9_TIMING_SUMMARY_ROW_COUNT")
            row = measured[0]
            avg_decode = float(row["avgDecodeTimeUs"])
            if (
                row["caseName"] != case_name
                or int(row["processedFrames"]) != args.timed_frames
                or not math.isfinite(avg_decode)
                or avg_decode <= 0.0
            ):
                raise SystemExit("BLOCKED_BCH16W9_INVALID_TIMING_RESULT")
            repetition_rows.append({
                "caseName": case_name,
                "payloadLength": payload_length,
                "encodedLength": int(source_row["encodedLength"]),
                "frameRate": source_row["frameRate"],
                "sourceEbN0Db": source_row["ebn0Db"],
                "sourceSnrIndex": source_row["snrIndex"],
                "repetition": repetition,
                "warmupFrames": args.warmup_frames,
                "timedFrames": args.timed_frames,
                "avgDecodeTimeUs": row["avgDecodeTimeUs"],
                "p50DecodeTimeUs": row["p50DecodeTimeUs"],
                "p95DecodeTimeUs": row["p95DecodeTimeUs"],
                "p99DecodeTimeUs": row["p99DecodeTimeUs"],
                "maxDecodeTimeUs": row["maxDecodeTimeUs"],
                "decodedBitErrors": row["decodedBitErrors"],
                "decodedFrameErrors": row["decodedFrameErrors"],
                "configHash": row["configHash"],
            })

    write_rows(args.output_dir / "timing_repetitions.csv", repetition_rows)
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in repetition_rows:
        grouped.setdefault((str(row["caseName"]), str(row["sourceEbN0Db"])), []).append(row)

    summary_rows: list[dict[str, object]] = []
    for source_row in source:
        key = (source_row["caseName"], source_row["ebn0Db"])
        rows = grouped[key]
        means = [float(row["avgDecodeTimeUs"]) for row in rows]
        median_mean = statistics.median(means)
        relative_span = (max(means) - min(means)) / median_mean
        summary_rows.append({
            "caseName": source_row["caseName"],
            "payloadLength": source_row["payloadLength"],
            "encodedLength": source_row["encodedLength"],
            "frameRate": source_row["frameRate"],
            "sourceEbN0Db": source_row["ebn0Db"],
            "sourceSnrIndex": source_row["snrIndex"],
            "warmupFrames": args.warmup_frames,
            "timedFramesPerRepetition": args.timed_frames,
            "repetitions": args.repetitions,
            "publishedAvgDecodeTimeUs": format(median_mean, ".17g"),
            "minAvgDecodeTimeUs": format(min(means), ".17g"),
            "maxAvgDecodeTimeUs": format(max(means), ".17g"),
            "relativeSpan": format(relative_span, ".17g"),
        })
    write_rows(args.output_dir / "timing_summary.csv", summary_rows)
    print(
        f"PASS_BCH16W9_TIMING points={len(source)} "
        f"measurements={len(repetition_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
