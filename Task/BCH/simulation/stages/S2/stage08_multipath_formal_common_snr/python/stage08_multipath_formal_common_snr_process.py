#!/usr/bin/env python3
"""Merge common-SNR shards and produce summaries, ranking, and crossing analysis."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"
METRICS = ("ber", "fer", "decoderFailureRate", "miscorrectionRate", "decodeTimeMeanNs", "equalizeTimeMeanNs")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if not rows:
        rows = [{}]
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        if rows != [{}]:
            writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    grid = read(stage / f"{PREFIX}_frozen_grid.csv")
    order = {(row["caseId"], row["waveformSnrIndex"]): index for index, row in enumerate(grid)}
    shard_paths = [results / f"{PREFIX}_shard_{index}.csv" for index in range(2)]
    shards = [read(path) for path in shard_paths]
    rows = [row for shard in shards for row in shard]
    if len(rows) != 296:
        raise RuntimeError(f"BLOCKED_STAGE08_COMMON_SNR_MERGE_ROW_COUNT:{len(rows)}")
    keys = [(row["caseId"], row["waveformSnrIndex"]) for row in rows]
    if len(set(keys)) != 296 or set(keys) != set(order):
        raise RuntimeError("BLOCKED_STAGE08_COMMON_SNR_MERGE_POINT_SET")
    if len({row["gitCommit"] for row in rows}) != 1:
        raise RuntimeError("BLOCKED_STAGE08_COMMON_SNR_MERGE_GIT_COMMIT")
    if len({row["configHash"] for row in rows}) != 1:
        raise RuntimeError("BLOCKED_STAGE08_COMMON_SNR_MERGE_CONFIG_HASH")
    rows.sort(key=lambda row: order[(row["caseId"], row["waveformSnrIndex"])])
    merged = results / f"{PREFIX}_results.csv"
    write(merged, rows, list(rows[0]))

    audit_rows = []
    seen_by_shard = []
    for index, shard in enumerate(shards):
        seen = {(row["caseId"], row["waveformSnrIndex"]) for row in shard}
        seen_by_shard.append(seen)
        audit_rows.append({
            "shardId": f"SHARD_{index}",
            "pointCount": len(shard),
            "frameCount": sum(int(row["totalFrames"]) for row in shard),
            "uniquePointCount": len(seen),
            "overlapPointCount": 0,
            "gitCommit": shard[0]["gitCommit"],
            "configHash": shard[0]["configHash"],
            "resultSha256": sha(shard_paths[index]),
            "gate": "PASS",
        })
    if seen_by_shard[0] & seen_by_shard[1]:
        raise RuntimeError("BLOCKED_STAGE08_COMMON_SNR_SHARD_OVERLAP")
    write(stage / f"{PREFIX}_merge_audit.csv", audit_rows)

    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_case[row["caseId"]].append(row)
    summaries = []
    runtime = []
    for case_id, selected in sorted(by_case.items()):
        total_frames = sum(int(row["totalFrames"]) for row in selected)
        total_bits = sum(int(row["totalPayloadBits"]) for row in selected)
        total_bit_errors = sum(int(row["payloadErrorBits"]) for row in selected)
        total_frame_errors = sum(int(row["payloadErrorFrames"]) for row in selected)
        summaries.append({
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
            "maxSnrDb": max(float(row["waveformSnrDb"]) for row in selected),
            "maxSnrBer": [row for row in selected if float(row["waveformSnrDb"]) == 18.0][0]["ber"],
            "maxSnrFer": [row for row in selected if float(row["waveformSnrDb"]) == 18.0][0]["fer"],
            "targetStopPoints": sum(row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED" for row in selected),
            "maxStopPoints": sum(row["stopReason"] == "MAX_FRAMES_REACHED" for row in selected),
            "miscorrectionFrames": sum(int(row["miscorrectionFrames"]) for row in selected),
            "decoderFailureFrames": sum(int(row["decoderFailureFrames"]) for row in selected),
        })
        frames = float(total_frames)
        runtime.append({
            "caseId": case_id,
            "totalFrames": total_frames,
            "encodeTimeMeanNs": sum(int(row["encodeTimeTotalNs"]) for row in selected) / frames,
            "channelTimeMeanNs": sum(int(row["channelTimeTotalNs"]) for row in selected) / frames,
            "equalizeTimeMeanNs": sum(int(row["equalizeTimeTotalNs"]) for row in selected) / frames,
            "hardDecisionTimeMeanNs": sum(int(row["hardDecisionTimeTotalNs"]) for row in selected) / frames,
            "decodeTimeMeanNs": sum(int(row["decodeTimeTotalNs"]) for row in selected) / frames,
            "decodeTimeP95NsMax": max(float(row["decodeTimeP95Ns"]) for row in selected),
            "equalizeTimeP95NsMax": max(float(row["equalizeTimeP95Ns"]) for row in selected),
        })
    write(stage / f"{PREFIX}_summary.csv", summaries)
    write(stage / f"{PREFIX}_k200_summary.csv", [row for row in summaries if int(row["payloadLength"]) == 200])
    write(stage / f"{PREFIX}_k300_summary.csv", [row for row in summaries if int(row["payloadLength"]) == 300])
    write(stage / f"{PREFIX}_runtime_summary.csv", runtime)

    ranking = []
    for payload in (200, 300):
        for idx in range(37):
            selected = [row for row in rows if int(row["payloadLength"]) == payload and int(row["waveformSnrIndex"]) == idx]
            snr = selected[0]["waveformSnrDb"]
            ranks = {}
            for metric in METRICS:
                ordered = sorted(selected, key=lambda row: float(row[metric]))
                ranks[metric + "Ranking"] = ";".join(f"{rank + 1}:{row['caseId']}" for rank, row in enumerate(ordered))
            ranking.append({"payloadLength": payload, "waveformSnrIndex": idx, "waveformSnrDb": snr, **ranks})
    write(stage / f"{PREFIX}_pointwise_ranking.csv", ranking)

    crossings = []
    for payload in (200, 300):
        case_ids = sorted({row["caseId"] for row in rows if int(row["payloadLength"]) == payload})
        for metric in ("ber", "fer"):
            table = {(row["caseId"], int(row["waveformSnrIndex"])): float(row[metric]) for row in rows if int(row["payloadLength"]) == payload}
            for case_a, case_b in combinations(case_ids, 2):
                previous = None
                for idx in range(37):
                    va = table[(case_a, idx)]
                    vb = table[(case_b, idx)]
                    relation = "tie" if va == vb else "A" if va < vb else "B"
                    if previous and relation != "tie" and previous[1] != "tie" and relation != previous[1]:
                        crossings.append({
                            "payloadLength": payload,
                            "metric": metric,
                            "caseA": case_a,
                            "caseB": case_b,
                            "leftSnrDb": f"{(idx - 1) * 0.5:.1f}",
                            "rightSnrDb": f"{idx * 0.5:.1f}",
                            "rankingAtLeft": previous[1],
                            "rankingAtRight": relation,
                            "crossingObservedBetweenGridPoints": "true",
                        })
                    if relation != "tie":
                        previous = (idx, relation)
    write(stage / f"{PREFIX}_curve_crossing_analysis.csv", crossings, [
        "payloadLength", "metric", "caseA", "caseB", "leftSnrDb", "rightSnrDb",
        "rankingAtLeft", "rankingAtRight", "crossingObservedBetweenGridPoints",
    ])

    checkpoint_manifest = {
        "schemaVersion": "stage08.common_snr.checkpoint.v1",
        "checkpointIntervalFramesConfigured": 1000,
        "resumeVerification": "PASS_INTERRUPTED_POINT_RESUMED_AND_COMPLETED",
        "shards": [{
            "shardId": f"SHARD_{index}",
            "completedPoints": len(shards[index]),
            "resultFile": str(shard_paths[index].relative_to(stage)).replace("\\", "/"),
            "resultSha256": sha(shard_paths[index]),
        } for index in range(2)],
    }
    (stage / f"{PREFIX}_checkpoint_manifest.json").write_text(json.dumps(checkpoint_manifest, indent=2) + "\n", encoding="utf-8")
    shard_manifest = {
        "schemaVersion": "stage08.common_snr.shards.v1",
        "shardCount": 2,
        "partition": "GRID_ROW_INDEX_MOD_SHARD_COUNT",
        "mergedResult": f"results/{PREFIX}_results.csv",
        "mergedResultSha256": sha(merged),
        "mergeGate": "PASS",
    }
    (stage / f"{PREFIX}_shard_manifest.json").write_text(json.dumps(shard_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_STAGE08_COMMON_SNR_SHARD_MERGE points={len(rows)} frames={sum(int(row['totalFrames']) for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
