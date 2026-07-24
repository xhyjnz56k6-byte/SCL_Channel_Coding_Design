#!/usr/bin/env python3
"""Audit and convert the frozen S1 five-case AWGN baseline without rerunning it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/s2_03_awgn_baseline_reuse"
    formal = repo / "Task/BCH/simulation/stages/bch16w8_five_case_comparison/five_case_formal_summary.csv"
    timing = repo / "Task/BCH/simulation/stages/bch16w9_decode_timing_snr_figures/timing_point_summary.csv"
    required_cases = {"BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"}
    if not formal.is_file() or not timing.is_file():
        raise SystemExit("BLOCKED_BCH_S2_03_AWGN_BASELINE_MISSING")
    rows = list(csv.DictReader(formal.open(newline="", encoding="utf-8")))
    timing_rows = list(csv.DictReader(timing.open(newline="", encoding="utf-8")))
    if {row["caseName"] for row in rows} != required_cases:
        raise SystemExit("BLOCKED_BCH_S2_03_AWGN_BASELINE_MISSING")
    source_rows: list[dict[str, object]] = []
    converted: list[dict[str, object]] = []
    for case in sorted(required_cases):
        selected = [row for row in rows if row["caseName"] == case]
        rates = {row["frameRate"] for row in selected}
        commits = {row["gitCommit"] for row in selected}
        if len(rates) != 1 or len(commits) != 1:
            raise SystemExit("BLOCKED_BCH_S2_03_AWGN_BASELINE_HASH_MISMATCH")
        stops = Counter(row["stopReason"] for row in selected)
        source_rows.append({
            "caseName": case,
            "sourcePath": formal.relative_to(repo).as_posix(),
            "sourceSha256": sha256(formal),
            "sourceGitCommit": next(iter(commits)),
            "schemaVersion": selected[0]["schemaVersion"],
            "payloadLength": selected[0]["payloadLength"],
            "encodedLength": selected[0]["encodedLength"],
            "frameRate": selected[0]["frameRate"],
            "pointCount": len(selected),
            "sourceEbN0Min": min(float(row["ebn0Db"]) for row in selected),
            "sourceEbN0Max": max(float(row["ebn0Db"]) for row in selected),
            "snrMin": min(float(row["ebn0Db"]) + 10 * math.log10(float(row["frameRate"])) for row in selected),
            "snrMax": max(float(row["ebn0Db"]) + 10 * math.log10(float(row["frameRate"])) for row in selected),
            "processedFrames": sum(int(row["processedFrames"]) for row in selected),
            "stopReasonDistribution": ";".join(f"{key}:{value}" for key, value in sorted(stops.items())),
            "berColumn": "BER",
            "ferColumn": "FER",
            "trueSuccessColumn": "trueSuccessRate",
            "miscorrectionColumn": "miscorrectionRate",
            "decoderFailureColumn": "decoderFailureRate",
            "timingSource": timing.relative_to(repo).as_posix(),
            "timingSourceSha256": sha256(timing),
            "auditStatus": "PASS",
        })
        for row in selected:
            converted_snr = float(row["ebn0Db"]) + 10 * math.log10(float(row["frameRate"]))
            converted.append({
                "caseName": case,
                "payloadLength": row["payloadLength"],
                "encodedLength": row["encodedLength"],
                "frameRate": row["frameRate"],
                "sourcePayloadEbN0Db": row["ebn0Db"],
                "snrDb": f"{converted_snr:.17g}",
                "processedFrames": row["processedFrames"],
                "decodedBitErrors": row["decodedBitErrors"],
                "decodedFrameErrors": row["decodedFrameErrors"],
                "BER": row["BER"],
                "FER": row["FER"],
                "trueSuccessRate": row["trueSuccessRate"],
                "reportedSuccessRate": row["reportedSuccessRate"],
                "miscorrectionRate": row["miscorrectionRate"],
                "decoderFailureRate": row["decoderFailureRate"],
                "stopReason": row["stopReason"],
                "sourceGitCommit": row["gitCommit"],
            })
    for row in converted:
        expected = float(row["sourcePayloadEbN0Db"]) + 10 * math.log10(float(row["frameRate"]))
        if abs(float(row["snrDb"]) - expected) >= 1e-12:
            raise SystemExit("BLOCKED_BCH_S2_03_SNR_CONVERSION_MISMATCH")
    write_rows(stage / "awgn_baseline_sources.csv", source_rows)
    write_rows(stage / "awgn_baseline_snr_converted.csv", converted)
    print("SKIPPED_BCH_S2_03_AWGN_RERUN")
    print("REUSED_S1_FORMAL_AWGN_BASELINE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
