#!/usr/bin/env python3
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import time


GROUPS = ("RATE_NEAR_2_3", "RATE_NEAR_1_2")
CHANNELS = (
    "AWGN",
    "FIXED_MULTIPATH_REAL_MMSE",
    "CFO_30_DEG",
    "LINEAR_TIME_VARYING_FREQUENCY",
    "KNOWN_BLOCKAGE_5_PERCENT",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB",
)
SCHEMES = (
    "CC_R23_BLOCK_FLOAT",
    "LDPC_BG2_N480_NMS",
    "CC_R12_BLOCK_FLOAT",
    "LDPC_BG2_N640_NMS",
)
ALLOWED_STOPS = {
    "PAIRED_TARGET_FRAME_ERRORS_REACHED",
    "PAIRED_MAX_FRAMES_REACHED",
    "RESUMED_PAIRED_TARGET_FRAME_ERRORS_REACHED",
    "RESUMED_PAIRED_MAX_FRAMES_REACHED",
    "SKIPPED_ALREADY_COMPLETE",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slug(group: str, channel: str, snr: float) -> str:
    snr_text = ("m" if snr < 0 else "p") + f"{abs(snr):04.1f}".replace(".", "p")
    return f"{group.lower()}__{channel.lower()}__{snr_text}"


def tasks(shards: int):
    result = []
    index = 0
    for group in GROUPS:
        for channel in CHANNELS:
            for half_db in range(-10, 21):
                snr = half_db / 2.0
                result.append({
                    "taskIndex": index,
                    "taskKey": f"{group}_{channel}_{snr:.1f}",
                    "group": group,
                    "channel": channel,
                    "esN0Db": snr,
                    "shardId": index % shards,
                    "slug": slug(group, channel, snr),
                })
                index += 1
    return result


def write_plan(output: pathlib.Path, rows, config_hash: str):
    output.mkdir(parents=True, exist_ok=True)
    with (output / "formal_execution_plan.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["taskIndex", "taskKey", "shardId", "group", "channel", "esN0Db",
                  "schemePointCount", "minFrames", "targetFrameErrors", "maxFrames",
                  "checkpointIntervalFrames", "configHash"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{key: row[key] for key in fields if key in row},
                             "schemePointCount": 2, "minFrames": 1000,
                             "targetFrameErrors": 200, "maxFrames": 50000,
                             "checkpointIntervalFrames": 1000, "configHash": config_hash})


def run_task(exe: pathlib.Path, output: pathlib.Path, row, config_hash: str, run_id: str):
    task_dir = output / f"shard_{row['shardId']}" / "tasks" / row["slug"]
    task_dir.mkdir(parents=True, exist_ok=True)
    command = [str(exe), "formal_task", str(task_dir), row["group"], row["channel"],
               f"{row['esN0Db']:.1f}", "1000", "200", "50000", config_hash, run_id]
    started = time.time()
    completed = subprocess.run(command, text=True, capture_output=True)
    log_text = ("COMMAND: " + subprocess.list2cmdline(command) + "\n" +
                completed.stdout + completed.stderr)
    (task_dir / "execution.log").write_text(log_text, encoding="utf-8")
    status = "PASS" if completed.returncode == 0 else "FAIL"
    manifest = {
        "schemaVersion": "s5.formal_task_manifest.v1",
        "taskKey": row["taskKey"],
        "shardId": row["shardId"],
        "group": row["group"],
        "channel": row["channel"],
        "esN0Db": row["esN0Db"],
        "configHash": config_hash,
        "status": status,
        "returnCode": completed.returncode,
        "elapsedSeconds": time.time() - started,
        "files": {},
    }
    for name in ("checkpoint.json", "timing_samples.csv", "final_result.csv", "execution.log"):
        path = task_dir / name
        if path.exists():
            manifest["files"][name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    (task_dir / "task_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return row, completed.returncode, completed.stdout.strip(), task_dir


def merge_and_audit(output: pathlib.Path, rows, config_hash: str):
    merged = []
    failures = []
    for task in rows:
        path = output / f"shard_{task['shardId']}" / "tasks" / task["slug"] / "final_result.csv"
        if not path.exists():
            failures.append(f"missing final result: {task['taskKey']}")
            continue
        with path.open(encoding="utf-8") as stream:
            task_rows = list(csv.DictReader(stream))
        if len(task_rows) != 2:
            failures.append(f"task row count != 2: {task['taskKey']}")
            continue
        for row in task_rows:
            row["shardId"] = str(task["shardId"])
            merged.append(row)
    expected = {
        (group, channel, f"{half / 2.0:.1f}", scheme)
        for group in GROUPS for channel in CHANNELS for half in range(-10, 21)
        for scheme in SCHEMES
        if (group == "RATE_NEAR_2_3" and scheme in SCHEMES[:2])
        or (group == "RATE_NEAR_1_2" and scheme in SCHEMES[2:])
    }
    keys = [(r["group"], r["channel"], f"{float(r['esN0Db']):.1f}", r["scheme"]) for r in merged]
    if len(merged) != 744:
        failures.append(f"merged row count {len(merged)} != 744")
    if len(set(keys)) != len(keys):
        failures.append("duplicate merged scheme point")
    missing = sorted(expected - set(keys))
    extra = sorted(set(keys) - expected)
    if missing:
        failures.append(f"missing scheme points: {missing[:5]} (total {len(missing)})")
    if extra:
        failures.append(f"unexpected scheme points: {extra[:5]} (total {len(extra)})")
    pair_frames = {}
    numeric_fields = (
        "BER", "FER", "berCiLow", "berCiHigh", "ferCiLow", "ferCiHigh",
        "avgChannelProcessingTimeUs", "medianChannelProcessingTimeUs",
        "p95ChannelProcessingTimeUs", "maxChannelProcessingTimeUs",
        "avgDecodeTimeUs", "medianDecodeTimeUs", "p95DecodeTimeUs", "maxDecodeTimeUs",
        "avgTotalReceiverAlgorithmTimeUs", "medianTotalReceiverAlgorithmTimeUs",
        "p95TotalReceiverAlgorithmTimeUs", "maxTotalReceiverAlgorithmTimeUs",
    )
    for row in merged:
        key = (row["group"], row["channel"], f"{float(row['esN0Db']):.1f}", row["scheme"])
        try:
            frames = int(row["frames"])
            bits = int(row["payloadBitErrors"])
            errors = int(row["frameErrors"])
            if not (1000 <= frames <= 50000):
                raise ValueError("frames outside frozen range")
            if abs(float(row["BER"]) - bits / (frames * 300)) > 1e-15:
                raise ValueError("BER/count mismatch")
            if abs(float(row["FER"]) - errors / frames) > 1e-15:
                raise ValueError("FER/count mismatch")
            if row["stopReason"] not in ALLOWED_STOPS:
                raise ValueError("invalid stop reason")
            if row["configHash"] != config_hash:
                raise ValueError("config hash mismatch")
            if row["noisePolicy"] != "s5_complex_pair_v1":
                raise ValueError("noise policy mismatch")
            if not all(math.isfinite(float(row[field])) for field in numeric_fields):
                raise ValueError("NaN/Inf")
            if float(row["p95DecodeTimeUs"]) > float(row["maxDecodeTimeUs"]):
                raise ValueError("decode p95 > max")
            if row["iterationsApplicable"] == "false":
                if any(row[field] != "NA" for field in
                       ("avgIterations", "medianIterations", "p95Iterations", "maxIterations",
                        "maxIterationFrames", "maxIterationRate")):
                    raise ValueError("CC iteration applicability violation")
            else:
                if not all(math.isfinite(float(row[field])) for field in
                           ("avgIterations", "medianIterations", "p95Iterations", "maxIterations",
                            "maxIterationFrames", "maxIterationRate")):
                    raise ValueError("LDPC iteration field invalid")
            pair_frames.setdefault(key[:3], set()).add(frames)
        except Exception as error:
            failures.append(f"{key}: {error}")
    for key, values in pair_frames.items():
        if len(values) != 1:
            failures.append(f"paired frame mismatch: {key} -> {sorted(values)}")
    merged.sort(key=lambda r: (r["group"], r["channel"], float(r["esN0Db"]), r["scheme"]))
    merged_dir = output / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    merged_path = merged_dir / "formal_merged_results.csv"
    if merged:
        with merged_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(merged[0]))
            writer.writeheader()
            writer.writerows(merged)
    report = {
        "schemaVersion": "s5.formal_merge_audit.v1",
        "expectedSchemePoints": 744,
        "actualSchemePoints": len(merged),
        "uniqueSchemePoints": len(set(keys)),
        "configHash": config_hash,
        "mergedResultSha256": sha256(merged_path) if merged_path.exists() else None,
        "failures": failures,
        "gate": "PASS_S5_FORMAL" if not failures else "FAIL_S5_FORMAL",
    }
    (merged_dir / "formal_merge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (merged_dir / "formal_merge_audit.md").write_text(
        "# S5 Formal merge audit\n\n"
        f"- Expected/actual: 744/{len(merged)}\n"
        f"- Unique: {len(set(keys))}\n"
        f"- Config hash: `{config_hash}`\n"
        f"- Failures: {len(failures)}\n"
        f"- Gate: **{report['gate']}**\n" +
        ("\n" + "\n".join(f"- {item}" for item in failures) + "\n" if failures else ""),
        encoding="utf-8")
    (merged_dir / "formal_gate.txt").write_text(report["gate"] + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=pathlib.Path, required=True)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--run-id", default="S5_FORMAL_20260802")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 4:
        raise RuntimeError("Formal requires at least four shards/workers")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["channels"] != list(CHANNELS) or config["formalSchemePointCount"] != 744:
        raise RuntimeError("frozen Formal config mismatch")
    config_hash = sha256(args.config)
    plan = tasks(args.workers)
    write_plan(args.output, plan, config_hash)
    if args.plan_only:
        print(f"PASS_S5_FORMAL_PLAN tasks={len(plan)} schemePoints=744 configHash={config_hash}")
        return 0
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(run_task, args.exe.resolve(), args.output.resolve(), row,
                               config_hash, args.run_id) for row in plan]
        for count, future in enumerate(concurrent.futures.as_completed(pending), 1):
            row, code, message, task_dir = future.result()
            print(f"[{count}/{len(plan)}] shard={row['shardId']} {row['taskKey']} rc={code} {message}", flush=True)
            if code != 0:
                failures.append({"taskKey": row["taskKey"], "returnCode": code,
                                 "taskDir": str(task_dir)})
    if failures:
        (args.output / "formal_execution_failures.json").write_text(
            json.dumps(failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("FAIL_S5_FORMAL_EXECUTION")
        return 1
    report = merge_and_audit(args.output, plan, config_hash)
    print(report["gate"])
    return 0 if report["gate"] == "PASS_S5_FORMAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
