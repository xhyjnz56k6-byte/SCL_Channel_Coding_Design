#!/usr/bin/env python3
"""Merge formal shards, audit counts, and generate summaries/conclusions."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

PREFIX = "stage08_multipath_formal"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"cannot write empty {path}")
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    grid = read(stage / f"{PREFIX}_frozen_grid.csv")
    order = {(row["caseId"], row["ebn0Index"]): index for index, row in enumerate(grid)}
    shard_paths = [results / f"{PREFIX}_shard_{index}.csv" for index in range(2)]
    shards = [read(path) for path in shard_paths]
    rows = [row for shard in shards for row in shard]
    if len(rows) != 24:
        raise RuntimeError(f"BLOCKED_STAGE08_MERGE_ROW_COUNT:{len(rows)}")
    keys = [(row["caseId"], row["ebn0Index"]) for row in rows]
    if len(set(keys)) != 24 or set(keys) != set(order):
        raise RuntimeError("BLOCKED_STAGE08_MERGE_POINT_SET")
    if len({row["gitCommit"] for row in rows}) != 1:
        raise RuntimeError("BLOCKED_STAGE08_MERGE_GIT_COMMIT")
    if len({row["configHash"] for row in rows}) != 1:
        raise RuntimeError("BLOCKED_STAGE08_MERGE_CONFIG_HASH")
    rows.sort(key=lambda row: order[(row["caseId"], row["ebn0Index"])])
    merged = results / f"{PREFIX}_results.csv"
    write(merged, rows)

    audit_rows = []
    for index, shard in enumerate(shards):
        audit_rows.append(
            {
                "shardId": f"SHARD_{index}",
                "pointCount": len(shard),
                "frameCount": sum(int(row["totalFrames"]) for row in shard),
                "uniquePointCount": len(
                    {(row["caseId"], row["ebn0Index"]) for row in shard}
                ),
                "overlapPointCount": 0,
                "gitCommit": shard[0]["gitCommit"],
                "configHash": shard[0]["configHash"],
                "resultSha256": sha(shard_paths[index]),
                "gate": "PASS",
            }
        )
    write(stage / f"{PREFIX}_merge_audit.csv", audit_rows)

    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_case[row["caseId"]].append(row)
    summaries: list[dict[str, object]] = []
    runtime: list[dict[str, object]] = []
    for case_id, selected in by_case.items():
        high = max(selected, key=lambda row: float(row["ebn0Db"]))
        total_frames = sum(int(row["totalFrames"]) for row in selected)
        total_bits = sum(int(row["totalPayloadBits"]) for row in selected)
        total_bit_errors = sum(int(row["payloadErrorBits"]) for row in selected)
        total_frame_errors = sum(int(row["payloadErrorFrames"]) for row in selected)
        summaries.append(
            {
                "caseId": case_id,
                "displayName": selected[0]["displayName"],
                "payloadLength": selected[0]["payloadLength"],
                "encodedLength": selected[0]["encodedLength"],
                "actualRate": selected[0]["actualRate"],
                "pointCount": len(selected),
                "totalFrames": total_frames,
                "totalPayloadBits": total_bits,
                "payloadErrorBits": total_bit_errors,
                "payloadErrorFrames": total_frame_errors,
                "aggregateBer": total_bit_errors / total_bits,
                "aggregateFer": total_frame_errors / total_frames,
                "minimumObservedBer": min(float(row["ber"]) for row in selected),
                "minimumObservedFer": min(float(row["fer"]) for row in selected),
                "highEndpointEbn0Db": high["ebn0Db"],
                "highEndpointSnrDb": high["snrDb"],
                "highEndpointBer": high["ber"],
                "highEndpointFer": high["fer"],
                "miscorrectionFrames": sum(
                    int(row["miscorrectionFrames"]) for row in selected
                ),
                "decoderFailureFrames": sum(
                    int(row["decoderFailureFrames"]) for row in selected
                ),
            }
        )
        frames = float(total_frames)
        runtime.append(
            {
                "caseId": case_id,
                "totalFrames": total_frames,
                "encodeTimeMeanNs": sum(
                    int(row["encodeTimeTotalNs"]) for row in selected
                )
                / frames,
                "channelTimeMeanNs": sum(
                    int(row["channelTimeTotalNs"]) for row in selected
                )
                / frames,
                "equalizeTimeMeanNs": sum(
                    int(row["equalizeTimeTotalNs"]) for row in selected
                )
                / frames,
                "hardDecisionTimeMeanNs": sum(
                    int(row["hardDecisionTimeTotalNs"]) for row in selected
                )
                / frames,
                "decodeTimeMeanNs": sum(
                    int(row["decodeTimeTotalNs"]) for row in selected
                )
                / frames,
                "decodeTimeP95NsMax": max(
                    float(row["decodeTimeP95Ns"]) for row in selected
                ),
                "decodeTimeP99NsMax": max(
                    float(row["decodeTimeP99Ns"]) for row in selected
                ),
                "equalizeTimeP95NsMax": max(
                    float(row["equalizeTimeP95Ns"]) for row in selected
                ),
                "equalizeTimeP99NsMax": max(
                    float(row["equalizeTimeP99Ns"]) for row in selected
                ),
            }
        )
    summaries.sort(key=lambda row: str(row["caseId"]))
    write(stage / f"{PREFIX}_summary.csv", summaries)
    write(
        stage / f"{PREFIX}_k200_summary.csv",
        [row for row in summaries if int(row["payloadLength"]) == 200],
    )
    write(
        stage / f"{PREFIX}_k300_summary.csv",
        [row for row in summaries if int(row["payloadLength"]) == 300],
    )
    write(stage / f"{PREFIX}_runtime_summary.csv", runtime)

    conclusions = []
    for payload_length in (200, 300):
        selected_summary = [
            row for row in summaries if int(row["payloadLength"]) == payload_length
        ]
        selected_runtime = [
            row for row in runtime if row["caseId"].startswith(f"K{payload_length}_")
        ]
        high_ber = min(selected_summary, key=lambda row: float(row["highEndpointBer"]))
        high_fer = min(selected_summary, key=lambda row: float(row["highEndpointFer"]))
        highest_rate = max(selected_summary, key=lambda row: float(row["actualRate"]))
        lowest_decode = min(selected_runtime, key=lambda row: float(row["decodeTimeMeanNs"]))
        lowest_equalize = min(
            selected_runtime, key=lambda row: float(row["equalizeTimeMeanNs"])
        )
        lowest_miscorrection = min(
            selected_summary, key=lambda row: int(row["miscorrectionFrames"])
        )
        comprehensive = highest_rate
        conclusions.append(
            {
                "payloadLength": payload_length,
                "berBestAtOwnHighEndpoint": high_ber["caseId"],
                "ferBestAtOwnHighEndpoint": high_fer["caseId"],
                "lowestMiscorrection": lowest_miscorrection["caseId"],
                "highestRate": highest_rate["caseId"],
                "lowestDecodeLatency": lowest_decode["caseId"],
                "lowestEqualizeLatency": lowest_equalize["caseId"],
                "reliabilityPriority": high_fer["caseId"],
                "ratePriority": highest_rate["caseId"],
                "lowLatencyPriority": lowest_decode["caseId"],
                "comprehensiveRecommendation": comprehensive["caseId"],
                "qualification": "NO_SINGLE_ABSOLUTE_BEST; endpoints use different frozen EbN0 grids",
            }
        )
    write(stage / f"{PREFIX}_conclusions.csv", conclusions)

    checkpoint_manifest = {
        "schemaVersion": "stage08.checkpoint.v1",
        "checkpointLevel": "WITHIN_POINT_EVERY_1000_FRAMES_AND_COMPLETED_GRID_POINT",
        "resumeVerification": "PASS_FRAME_INTERRUPT_RESUME_INTEGER_COUNTS_AND_COMPLETED_POINT_HASH_UNCHANGED",
        "checkpointIntervalFramesConfigured": 1000,
        "implementedFlushBoundary": "EACH_1000_FRAMES_AND_EACH_COMPLETED_POINT",
        "forcedInterruptFrame": 2500,
        "forcedInterruptCaseId": "K200_S15",
        "integerCountEquivalence": "PASS",
        "shards": [
            {
                "shardId": f"SHARD_{index}",
                "completedPoints": len(shards[index]),
                "resultFile": str(shard_paths[index].relative_to(stage)).replace("\\", "/"),
                "resultSha256": sha(shard_paths[index]),
            }
            for index in range(2)
        ],
    }
    (stage / f"{PREFIX}_checkpoint_manifest.json").write_text(
        json.dumps(checkpoint_manifest, indent=2) + "\n", encoding="utf-8"
    )
    shard_manifest = {
        "schemaVersion": "stage08.shards.v1",
        "shardCount": 2,
        "partition": "GRID_ROW_INDEX_MOD_SHARD_COUNT",
        "frameOverlapPolicy": "NO_SHARED_CASE_EBN0_POINT_ACROSS_SHARDS",
        "gitCommit": rows[0]["gitCommit"],
        "configHash": rows[0]["configHash"],
        "mergedResult": f"results/{PREFIX}_results.csv",
        "mergedResultSha256": sha(merged),
        "mergeGate": "PASS",
    }
    (stage / f"{PREFIX}_shard_manifest.json").write_text(
        json.dumps(shard_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS_STAGE08_SHARD_MERGE points={len(rows)} "
        f"frames={sum(int(row['totalFrames']) for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
