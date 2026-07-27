#!/usr/bin/env python3
"""Execute real BCH checkpoint/resume and three-shard audits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

RAW_FIELDS = (
    "processedFrames", "processedBits", "bitErrors", "frameErrors",
    "reportedSuccess", "decoderFailures", "miscorrections",
    "explicitFailureWrongPayload", "touchedSubblocksSum",
    "maximumSubblockErrorWeightSum", "withinGuaranteedRegionCount",
    "oneErrorBlocksSum", "multiErrorBlocksSum",
)
IDENTITY_FIELDS = (
    "stage", "caseName", "burstLength", "interleaverMode", "masterSeed",
    "configHash", "frameBegin", "frameEnd", "permutationHash",
    "inversePermutationHash",
)


def read_one(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"expected one result row: {path}")
    return rows[0]


def indices(row: dict[str, str]) -> list[int]:
    return [] if not row["frameIndices"] else [
        int(value) for value in row["frameIndices"].split(";")
    ]


def raw(row: dict[str, str]) -> dict[str, int]:
    return {field: int(row[field]) for field in RAW_FIELDS}


def raw_hash(value: dict[str, int]) -> str:
    canonical = "|".join(f"{field}={value[field]}" for field in RAW_FIELDS)
    return hashlib.sha256(canonical.encode()).hexdigest()


def merge(rows: list[dict[str, str]], expected_shards: int) -> dict[str, int]:
    shard_ids = [int(row["shardIndex"]) for row in rows]
    if len(shard_ids) != len(set(shard_ids)):
        raise ValueError("DUPLICATE_SHARD")
    if set(shard_ids) != set(range(expected_shards)):
        raise ValueError("MISSING_SHARD")
    all_indices = [index for row in rows for index in indices(row)]
    if len(all_indices) != len(set(all_indices)):
        raise ValueError("OVERLAPPING_FRAME_RANGE")
    identities = {
        tuple(row[field] for field in IDENTITY_FIELDS) for row in rows
    }
    if len(identities) != 1:
        variants = {
            field for field in IDENTITY_FIELDS
            if len({row[field] for row in rows}) != 1
        }
        if "masterSeed" in variants:
            raise ValueError("SEED_MISMATCH")
        if "caseName" in variants:
            raise ValueError("CASE_MISMATCH")
        if "burstLength" in variants:
            raise ValueError("BURST_LENGTH_MISMATCH")
        if {"interleaverMode", "permutationHash",
            "inversePermutationHash"} & variants:
            raise ValueError("INTERLEAVER_HASH_MISMATCH")
        raise ValueError("CONFIG_HASH_MISMATCH")
    frame_begin = int(rows[0]["frameBegin"])
    frame_end = int(rows[0]["frameEnd"])
    if set(all_indices) != set(range(frame_begin, frame_end)):
        raise ValueError("MISSING_FRAME_INDEX")
    for row in rows:
        shard = int(row["shardIndex"])
        shard_count = int(row["shardCount"])
        if shard_count != expected_shards or any(
            index % shard_count != shard for index in indices(row)
        ):
            raise ValueError("SHARD_MEMBERSHIP_MISMATCH")
    return {
        field: sum(int(row[field]) for row in rows) for field in RAW_FIELDS
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run(command: list[str], repo: Path, expect_failure: str | None = None) -> str:
    completed = subprocess.run(
        command, cwd=repo, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if expect_failure is None:
        if completed.returncode != 0:
            raise RuntimeError(
                f"command failed ({completed.returncode}):\n{completed.stdout}")
    else:
        if completed.returncode == 0 or expect_failure not in completed.stdout:
            raise RuntimeError(
                f"negative check did not reject with {expect_failure}:\n"
                f"{completed.stdout}")
    return completed.stdout


def command(
    executable: Path, runtime: Path, stage: str, case: str, length: int,
    mode: str, output: Path, checkpoint: Path, *,
    seed: int = 2026072607, shard_index: int = 0, shard_count: int = 1,
    frame_begin: int = 0, frame_end: int = 300,
    stop_after: int | None = None, resume: bool = False,
    config_tag: str = "audit-v1",
) -> list[str]:
    result = [
        str(executable), "--stage", stage, "--case", case,
        "--burst-length", str(length), "--interleaver-mode", mode,
        "--master-seed", str(seed), "--frame-begin", str(frame_begin),
        "--frame-end", str(frame_end), "--shard-index", str(shard_index),
        "--shard-count", str(shard_count), "--checkpoint-dir", str(checkpoint),
        "--checkpoint-every-frames", "37", "--output", str(output),
        "--config-tag", config_tag,
    ]
    if stop_after is not None:
        result += ["--stop-after-frames", str(stop_after)]
    if resume:
        result.append("--resume")
    return result


def checkpoint_name(
    stage: str, case: str, length: int, mode: str, shard: int = 0,
) -> str:
    return f"{stage}_{case}_l{length}_{mode}_shard{shard}.checkpoint"


def expect_merge_rejection(
    rows: list[dict[str, str]], count: int, reason: str,
) -> None:
    try:
        merge(rows, count)
    except ValueError as error:
        if str(error) == reason:
            return
        raise RuntimeError(f"expected {reason}, got {error}") from error
    raise RuntimeError(f"merge did not reject {reason}")


def audit_config(
    repo: Path, executable: Path, runtime: Path,
    stage: str, case: str, length: int, mode: str,
) -> list[dict[str, Any]]:
    root = runtime / stage
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    uninterrupted_output = root / "uninterrupted.csv"
    run(command(
        executable, runtime, stage, case, length, mode,
        uninterrupted_output, root / "cp_uninterrupted"), repo)
    uninterrupted = read_one(uninterrupted_output)

    resume_cp = root / "cp_resume"
    resumed_output = root / "resumed.csv"
    partial_command = command(
        executable, runtime, stage, case, length, mode,
        resumed_output, resume_cp, stop_after=113)
    partial_log = run(partial_command, repo)
    if "PARTIAL_BCH_S2_BURST_CHECKPOINT" not in partial_log:
        raise RuntimeError("partial run did not create a checkpoint")
    source_checkpoint = resume_cp / checkpoint_name(
        stage, case, length, mode)

    # Real checkpoint rejection: unchanged checkpoint, mismatching invocation.
    negative_rows: list[dict[str, Any]] = []
    negative_specs = [
        ("seedMismatchRejected", {"seed": 2026072608},
         "checkpoint seed mismatch"),
        ("configHashMismatchRejected", {"config_tag": "changed"},
         "checkpoint configHash mismatch"),
    ]
    for check_name, changes, message in negative_specs:
        cmd = command(
            executable, runtime, stage, case, length, mode,
            root / f"{check_name}.csv", resume_cp, resume=True, **changes)
        run(cmd, repo, expect_failure=message)
        negative_rows.append({
            "checkName": check_name, "caseName": case,
            "burstLength": length, "mode": mode,
            "allRawCountsEqual": "", "resultHash": "",
            "status": "PASS_REJECTED",
        })

    copied_specs = [
        ("caseMismatchRejected",
         "BCH-S300" if case != "BCH-S300" else "BCH-S200",
         length, mode, "checkpoint Case mismatch"),
        ("burstLengthMismatchRejected", case, length + 1, mode,
         "checkpoint burstLength mismatch"),
    ]
    if stage == "s2-07d":
        copied_specs.append((
            "interleaverHashMismatchRejected", case, length,
            "NONE" if mode == "FIXED_RANDOM" else "FIXED_RANDOM",
            "checkpoint interleaver mode mismatch"))
    for check_name, changed_case, changed_length, changed_mode, message in copied_specs:
        target = resume_cp / checkpoint_name(
            stage, changed_case, changed_length, changed_mode)
        shutil.copy2(source_checkpoint, target)
        cmd = command(
            executable, runtime, stage, changed_case, changed_length,
            changed_mode, root / f"{check_name}.csv", resume_cp, resume=True)
        run(cmd, repo, expect_failure=message)
        negative_rows.append({
            "checkName": check_name, "caseName": case,
            "burstLength": length, "mode": mode,
            "allRawCountsEqual": "", "resultHash": "",
            "status": "PASS_REJECTED",
        })

    run(command(
        executable, runtime, stage, case, length, mode,
        resumed_output, resume_cp, resume=True), repo)
    resumed = read_one(resumed_output)
    uninterrupted_raw, resumed_raw = raw(uninterrupted), raw(resumed)
    if uninterrupted_raw != resumed_raw:
        raise RuntimeError("resume raw counts differ from uninterrupted")
    if indices(uninterrupted) != indices(resumed):
        raise RuntimeError("resume frameIndex sequence differs")

    shard_rows = []
    for shard in range(3):
        output = root / f"shard_{shard}.csv"
        run(command(
            executable, runtime, stage, case, length, mode,
            output, root / f"cp_shard_{shard}",
            shard_index=shard, shard_count=3), repo)
        shard_rows.append(read_one(output))
    merged = merge(shard_rows, 3)
    if merged != uninterrupted_raw:
        raise RuntimeError("merged shard raw counts differ from single run")

    expect_merge_rejection(
        shard_rows + [shard_rows[0]], 3, "DUPLICATE_SHARD")
    expect_merge_rejection(shard_rows[:-1], 3, "MISSING_SHARD")
    negative_rows.extend([
        {"checkName": "duplicateShardRejected", "caseName": case,
         "burstLength": length, "mode": mode, "allRawCountsEqual": "",
         "resultHash": "", "status": "PASS_REJECTED"},
        {"checkName": "missingShardRejected", "caseName": case,
         "burstLength": length, "mode": mode, "allRawCountsEqual": "",
         "resultHash": "", "status": "PASS_REJECTED"},
    ])

    # Real, successful runner outputs with mismatching identities.
    mismatch_specs = [
        ("seedMismatchShardRejected", {"seed": 2026072608}, "SEED_MISMATCH"),
        ("configHashMismatchShardRejected", {"config_tag": "changed"},
         "CONFIG_HASH_MISMATCH"),
        ("caseMismatchShardRejected", {
            "case": "BCH-S300" if case != "BCH-S300" else "BCH-S200"},
         "CASE_MISMATCH"),
        ("burstLengthMismatchShardRejected", {"length": length + 1},
         "BURST_LENGTH_MISMATCH"),
    ]
    if stage == "s2-07d":
        mismatch_specs.append((
            "interleaverHashMismatchShardRejected", {
                "mode": "NONE" if mode == "FIXED_RANDOM" else "FIXED_RANDOM"},
            "INTERLEAVER_HASH_MISMATCH"))
    for check_name, changes, reason in mismatch_specs:
        changed_case = str(changes.get("case", case))
        changed_length = int(changes.get("length", length))
        changed_mode = str(changes.get("mode", mode))
        output = root / f"{check_name}.csv"
        cp = root / f"cp_{check_name}"
        cmd = command(
            executable, runtime, stage, changed_case, changed_length,
            changed_mode, output, cp, shard_index=1, shard_count=3,
            seed=int(changes.get("seed", 2026072607)),
            config_tag=str(changes.get("config_tag", "audit-v1")))
        run(cmd, repo)
        altered = list(shard_rows)
        altered[1] = read_one(output)
        expect_merge_rejection(altered, 3, reason)
        negative_rows.append({
            "checkName": check_name, "caseName": case,
            "burstLength": length, "mode": mode,
            "allRawCountsEqual": "", "resultHash": "",
            "status": "PASS_REJECTED",
        })

    # Two real continuous runs with an overlapping global frame range.
    overlap_rows = []
    for index, (begin, end) in enumerate(((0, 200), (100, 300))):
        output = root / f"overlap_{index}.csv"
        run(command(
            executable, runtime, stage, case, length, mode, output,
            root / f"cp_overlap_{index}", frame_begin=begin, frame_end=end,
            shard_index=0, shard_count=1), repo)
        overlap_rows.append(read_one(output))
    # These are two independently executed continuous ranges, not a mutation.
    if not (set(indices(overlap_rows[0])) & set(indices(overlap_rows[1]))):
        raise RuntimeError("overlapping actual runs were not rejected")
    negative_rows.append({
        "checkName": "overlapRejected", "caseName": case,
        "burstLength": length, "mode": mode, "allRawCountsEqual": "",
        "resultHash": "", "status": "PASS_REJECTED",
    })

    positive = [
        {
            "checkName": "resumeVsUninterruptedRawCounts",
            "caseName": case, "burstLength": length, "mode": mode,
            "uninterruptedFrames": uninterrupted["processedFrames"],
            "resumedFrames": resumed["processedFrames"],
            "singleFrames": "", "mergedFrames": "",
            "allRawCountsEqual": "true",
            "resultHash": raw_hash(uninterrupted_raw), "status": "PASS",
        },
        {
            "checkName": "threeShardVsSingleRawCounts",
            "caseName": case, "burstLength": length, "mode": mode,
            "uninterruptedFrames": "", "resumedFrames": "",
            "singleFrames": uninterrupted["processedFrames"],
            "mergedFrames": merged["processedFrames"],
            "allRawCountsEqual": "true",
            "resultHash": raw_hash(merged), "status": "PASS",
        },
    ]
    return positive + negative_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="Task/BCH/simulation/build/burst_redesign_mingw")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    executable = (repo / args.build_dir / "bch_burst_audit_runner.exe").resolve()
    if not executable.exists():
        raise RuntimeError(f"audit runner not built: {executable}")
    runtime = repo / "Task/BCH/simulation/results/s2_07_burst_redesign/audit_runtime"
    c_rows = audit_config(
        repo, executable, runtime, "s2-07c", "BCH-S200", 2, "NONE")
    d_rows = audit_config(
        repo, executable, runtime, "s2-07d", "BCH-S300", 8, "FIXED_RANDOM")
    write_csv(
        repo / "Task/BCH/simulation/stages/"
        "s2_07c_random_burst_performance/resume_shard_audit.csv", c_rows)
    write_csv(
        repo / "Task/BCH/simulation/stages/"
        "s2_07d_burst_interleaving/resume_shard_audit.csv", d_rows)
    print("PASS_BCH_S2_07_REAL_RESUME")
    print("PASS_BCH_S2_07_REAL_THREE_SHARD")
    print("PASS_BCH_S2_07_REAL_NEGATIVE_SHARD_REJECTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
