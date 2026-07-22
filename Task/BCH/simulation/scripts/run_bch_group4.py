#!/usr/bin/env python3
"""Ordered BCH Group 4 build and experiment driver."""

from __future__ import annotations

import argparse
import csv
import math
import json
import shutil
import subprocess
import sys
from pathlib import Path


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300"]
SMOKE_SNR = [0.0, 2.0, 4.0, 6.0, 8.0]
PRESCAN_SNR = [index * 0.5 for index in range(21)]


def run(command: list[str], cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def append_csv(source: Path, writer: csv.DictWriter[str], include_header: bool = False) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if include_header:
            writer.writeheader()
        for row in reader:
            writer.writerow(row)


def ensure_pool(repo: Path, output: Path, payload: int, frames: int, seed: int) -> Path:
    manifest = output / f"k{payload}" / "manifest.json"
    if not manifest.exists():
        run([sys.executable, str(repo / "Task/Common/scripts/generate_common03_frame_pool.py"),
             "--output-dir", str(output), "--payload-length", str(payload), "--frame-count", str(frames),
             "--shard-size", str(min(1000, frames)), "--master-seed", str(seed), "--overwrite"], repo)
    return manifest


def execute_point(repo: Path, executable: Path, output: Path, stage: str, case: str, snr: float, snr_index: int,
                  frames: int, seed: int, manifest: Path, progress: bool, refresh: float,
                  detail: bool, frame_start: int = 0, extra_args: list[str] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    command = [str(executable), "--stage", stage, "--case", case, "--ebn0-db", str(snr),
               "--snr-index", str(snr_index), "--frame-start", str(frame_start), "--frame-count", str(frames),
               "--global-seed", str(seed), "--frame-pool-manifest", str(manifest),
               "--output-dir", str(output), "--progress-refresh-seconds", str(refresh),
               "--progress" if progress else "--no-progress"]
    if detail:
        command.append("--detail")
    if extra_args:
        command.extend(extra_args)
    run(command, repo)


def combine_files(points: list[Path], filename: str, target: Path) -> None:
    first = True
    with target.open("w", encoding="utf-8", newline="") as output:
        for point in points:
            lines = (point / filename).read_text(encoding="utf-8").splitlines()
            if not lines:
                continue
            if first:
                output.write(lines[0] + "\n")
                first = False
            for line in lines[1:]:
                output.write(line + "\n")


def combine_jsonl(points: list[Path], filename: str, target: Path) -> None:
    with target.open("w", encoding="utf-8", newline="") as output:
        for point in points:
            text = (point / filename).read_text(encoding="utf-8")
            output.write(text)
            if text and not text.endswith("\n"):
                output.write("\n")


def run_bch12(args: argparse.Namespace, repo: Path, build: Path, results: Path) -> None:
    executable = build / "bch_awgn_runner.exe"
    if not executable.exists():
        raise SystemExit("bch_awgn_runner.exe is missing; build the simulation first")
    smoke = results / "smoke"
    if smoke.exists():
        shutil.rmtree(smoke)
    smoke.mkdir(parents=True)
    pools = results / "frame_pools"
    manifests = {200: ensure_pool(repo, pools / "smoke_k200", 200, 200, args.payload_seed),
                 300: ensure_pool(repo, pools / "smoke_k300", 300, 200, args.payload_seed)}
    print("[2/6] BCH-12 execution plan")
    print(f"Cases: 4 | SNR points: 5 | case-points: 20 | fixed frames/point: 200 | maximum frames: 4000")
    print(f"Progress: {'enabled' if args.progress else 'disabled'} refresh={args.progress_refresh_seconds}s | Output: {smoke}")
    points: list[Path] = []
    reruns: list[Path] = []
    completed = 0
    for case in CASES:
        payload = 200 if case.endswith("200") else 300
        for snr_index, snr in enumerate(SMOKE_SNR):
            name = f"{case.lower().replace('-', '_')}_{snr_index:02d}"
            point = smoke / "points" / name
            rerun = smoke / "reproducibility" / name
            execute_point(repo, executable, point, "BCH12", case, snr, snr_index, 200, args.global_seed,
                          manifests[payload], args.progress, args.progress_refresh_seconds, True)
            execute_point(repo, executable, rerun, "BCH12", case, snr, snr_index, 200, args.global_seed,
                          manifests[payload], False, args.progress_refresh_seconds, True)
            points.append(point)
            reruns.append(rerun)
            completed += 1
            print(f"\r[BCH-12] case-points {completed}/20", end="", flush=True)
    print()
    combine_files(points, "summary.csv", smoke / "awgn_smoke_summary.csv")
    combine_files(points, "frame_detail.csv", smoke / "awgn_smoke_frame_detail.csv")
    combine_jsonl(points, "progress.jsonl", smoke / "progress.jsonl")

    summaries = list(csv.DictReader((smoke / "awgn_smoke_summary.csv").open(newline="", encoding="utf-8")))
    details = list(csv.DictReader((smoke / "awgn_smoke_frame_detail.csv").open(newline="", encoding="utf-8")))
    if len(summaries) != 20 or len(details) != 4000:
        raise SystemExit("BLOCKED_BCH12_RESULT_ACCOUNTING_FAILURE")
    key_rows = {(row["caseName"], row["ebn0Db"]): row for row in summaries}
    if len(key_rows) != 20 or any(not math.isfinite(float(row[field])) for row in summaries
                                  for field in ["BER", "FER", "noiseSigma", "noiseVariance"]):
        raise SystemExit("BLOCKED_BCH12_RESULT_ACCOUNTING_FAILURE")

    uniqueness_rows: list[dict[str, object]] = []
    reproducibility_rows: list[dict[str, object]] = []
    scaling_rows: list[dict[str, object]] = []
    for point, rerun in zip(points, reruns):
        primary = list(csv.DictReader((point / "frame_detail.csv").open(newline="", encoding="utf-8")))
        repeated = list(csv.DictReader((rerun / "frame_detail.csv").open(newline="", encoding="utf-8")))
        hashes = [row["noiseHash"] for row in primary]
        uniqueness_rows.append({"caseName": primary[0]["caseName"], "ebn0Db": primary[0]["ebn0Db"],
                                "frames": len(hashes), "uniqueNoiseHashes": len(set(hashes)),
                                "duplicateNoiseHashes": len(hashes) - len(set(hashes)), "status": "PASS" if len(set(hashes)) == len(hashes) else "FAIL"})
        hash_mismatch = sum(a["noiseHash"] != b["noiseHash"] for a, b in zip(primary, repeated))
        count_fields = ["channelHardBitErrors", "decodedBitErrors", "trueSuccess", "reportedSuccess", "miscorrected", "decoderFailure", "frameStatus"]
        count_mismatch = sum(any(a[field] != b[field] for field in count_fields) for a, b in zip(primary, repeated))
        reproducibility_rows.append({"caseName": primary[0]["caseName"], "ebn0Db": primary[0]["ebn0Db"],
                                     "frames": len(primary), "noiseHashMismatches": hash_mismatch,
                                     "resultMismatches": count_mismatch, "status": "PASS" if hash_mismatch + count_mismatch == 0 else "FAIL"})
        summary = next(csv.DictReader((point / "summary.csv").open(newline="", encoding="utf-8")))
        rate = float(summary["frameRate"])
        reference = math.sqrt(1.0 / (2.0 * rate * 10.0 ** (float(summary["ebn0Db"]) / 10.0)))
        computed = float(summary["noiseSigma"])
        difference = abs(computed - reference)
        scaling_rows.append({"caseName": summary["caseName"], "ebn0Db": summary["ebn0Db"],
                             "computedSigma": f"{computed:.17g}", "independentReferenceSigma": f"{reference:.17g}",
                             "absoluteDifference": f"{difference:.17g}",
                             "relativeDifference": f"{difference / reference:.17g}",
                             "status": "PASS" if difference <= 1e-15 * max(1.0, reference) else "FAIL"})
    for path, rows in [(smoke / "noise_uniqueness.csv", uniqueness_rows),
                       (smoke / "noise_reproducibility.csv", reproducibility_rows),
                       (smoke / "noise_scaling_audit.csv", scaling_rows)]:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    if any(row["status"] != "PASS" for row in uniqueness_rows):
        raise SystemExit("BLOCKED_BCH12_NOISE_REUSED_ACROSS_FRAMES")
    if any(row["status"] != "PASS" for row in reproducibility_rows):
        raise SystemExit("BLOCKED_BCH12_NOISE_NOT_REPRODUCIBLE")
    if any(row["status"] != "PASS" for row in scaling_rows):
        raise SystemExit("BLOCKED_BCH12_SIGMA_RATE_SCALING_ERROR")
    low_errors = sum(int(row["decodedFrameErrors"]) for row in summaries if float(row["ebn0Db"]) == 0.0)
    high_errors = sum(int(row["decodedFrameErrors"]) for row in summaries if float(row["ebn0Db"]) == 8.0)
    if low_errors <= high_errors:
        raise SystemExit("BCH-12 aggregate 0 dB performance is not worse than 8 dB")
    run([sys.executable, str(repo / "Task/BCH/simulation/scripts/plot_bch_smoke.py"),
         "--summary", str(smoke / "awgn_smoke_summary.csv"), "--output-dir", str(smoke)], repo)
    print(f"PASS_BCH12_AWGN_SMOKE frames=4000 casePoints=20 lowFE={low_errors} highFE={high_errors}")


def nearest_measured(case_rows: list[dict[str, str]], target: float) -> dict[str, str]:
    def distance(row: dict[str, str]) -> float:
        fer = float(row["FER"])
        if fer <= 0.0:
            fer = 0.5 / float(row["processedFrames"])
        return abs(math.log10(fer) - math.log10(target))
    return min(case_rows, key=distance)


def run_bch13(args: argparse.Namespace, repo: Path, build: Path, results: Path) -> None:
    executable = build / "bch_awgn_runner.exe"
    prescan = results / "prescan"
    if prescan.exists(): shutil.rmtree(prescan)
    prescan.mkdir(parents=True)
    pools = results / "frame_pools"
    manifests = {200: ensure_pool(repo, pools / "prescan_k200", 200, 2000, args.payload_seed),
                 300: ensure_pool(repo, pools / "prescan_k300", 300, 2000, args.payload_seed)}
    print("[3/6] BCH-13 execution plan")
    print(f"Cases: 4 | SNR points: 21 | case-points: 84 | fixed frames/point: 2000 | maximum frames: 168000")
    print(f"Progress: {'enabled' if args.progress else 'disabled'} refresh={args.progress_refresh_seconds}s | Output: {prescan}")
    points: list[Path] = []
    completed = 0
    for case in CASES:
        payload = 200 if case.endswith("200") else 300
        for snr_index, snr in enumerate(PRESCAN_SNR):
            point = prescan / "points" / f"{case.lower().replace('-', '_')}_{snr_index:02d}"
            execute_point(repo, executable, point, "BCH13", case, snr, snr_index, 2000, args.global_seed,
                          manifests[payload], args.progress, args.progress_refresh_seconds, False)
            points.append(point); completed += 1
            print(f"\r[BCH-13] case-points {completed}/84", end="", flush=True)
    print()
    combine_files(points, "summary.csv", prescan / "prescan_summary.csv")
    combine_jsonl(points, "progress.jsonl", prescan / "progress.jsonl")
    summaries = list(csv.DictReader((prescan / "prescan_summary.csv").open(newline="", encoding="utf-8")))
    keys = {(row["caseName"], float(row["ebn0Db"])) for row in summaries}
    if len(summaries) != 84 or len(keys) != 84 or sum(int(row["processedFrames"]) for row in summaries) != 168000:
        raise SystemExit("BLOCKED_BCH13_RESULT_ACCOUNTING_FAILURE")
    numeric = ["BER", "FER", "trueSuccessRate", "reportedSuccessRate", "miscorrectionRate", "decoderFailureRate", "avgDecodeTimeUs"]
    if any(not math.isfinite(float(row[field])) for row in summaries for field in numeric):
        raise SystemExit("BLOCKED_BCH13_RESULT_ACCOUNTING_FAILURE")

    recommendations: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    for case in CASES:
        selected = sorted((row for row in summaries if row["caseName"] == case), key=lambda row: float(row["ebn0Db"]))
        low = nearest_measured(selected, 0.5)
        mid = nearest_measured(selected, 0.1)
        high = nearest_measured(selected, 0.01)
        near_1e3 = nearest_measured(selected, 0.001)
        formal_min = min(float(low["ebn0Db"]), float(mid["ebn0Db"]), float(high["ebn0Db"]))
        formal_max = max(float(high["ebn0Db"]), float(near_1e3["ebn0Db"]))
        if formal_max <= formal_min:
            raise SystemExit("BLOCKED_BCH13_INVALID_PRESCAN_RANGE")
        recommendations.append({"caseName": case, "originalRange": "0.0:10.0:0.5", "actualRange": "0.0:10.0:0.5",
                                "adjustmentReason": "NO_ADJUSTMENT", "recommendedFormalMinDb": formal_min,
                                "recommendedFormalMaxDb": formal_max, "recommendedFormalStepDb": 0.2,
                                "estimatedRuntimeSeconds": round((formal_max - formal_min) / 0.2 + 1) * float(selected[0]["avgDecodeTimeUs"]) * 50000 / 1e6,
                                "waterfallLowDb": low["ebn0Db"], "waterfallLowFer": low["FER"],
                                "waterfallMidDb": mid["ebn0Db"], "waterfallMidFer": mid["FER"],
                                "waterfallHighDb": high["ebn0Db"], "waterfallHighFer": high["FER"],
                                "nearFer1e3Db": near_1e3["ebn0Db"], "nearFer1e3Observed": near_1e3["FER"],
                                "interpolationOrExtrapolation": "NONE_MEASURED_POINTS_ONLY"})
        status_rows.append({"caseName": case, "noErrorStatusFrames": sum(int(row["noErrorStatusFrames"]) for row in selected),
                            "correctedStatusFrames": sum(int(row["correctedStatusFrames"]) for row in selected),
                            "failedStatusFrames": sum(int(row["failedStatusFrames"]) for row in selected),
                            "miscorrectedFrames": sum(int(row["miscorrectedFrames"]) for row in selected),
                            "decoderFailureFrames": sum(int(row["decoderFailureFrames"]) for row in selected)})
        timing_rows.append({"caseName": case, "casePoints": 21, "processedFrames": 42000,
                            "meanOfPointAvgEncodeTimeUs": sum(float(row["avgEncodeTimeUs"]) for row in selected) / 21,
                            "meanOfPointAvgDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) for row in selected) / 21,
                            "maxPointP99DecodeTimeUs": max(float(row["p99DecodeTimeUs"]) for row in selected),
                            "maxDecodeTimeUs": max(float(row["maxDecodeTimeUs"]) for row in selected)})
    for path, output_rows in [(prescan / "prescan_case_recommendations.csv", recommendations),
                              (prescan / "prescan_status_distribution.csv", status_rows),
                              (prescan / "prescan_timing_summary.csv", timing_rows)]:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output_rows[0])); writer.writeheader(); writer.writerows(output_rows)
    run([sys.executable, str(repo / "Task/BCH/simulation/scripts/plot_bch_prescan.py"),
         "--summary", str(prescan / "prescan_summary.csv"), "--output-dir", str(prescan)], repo)
    print("PASS_BCH13_AWGN_PRESCAN frames=168000 casePoints=84")


RAW_COUNTERS = ["processedFrames", "processedPayloadBits", "channelHardBitErrors", "channelHardFrameErrors",
                "decodedBitErrors", "decodedFrameErrors", "trueSuccessFrames", "reportedSuccessFrames",
                "miscorrectedFrames", "decoderFailureFrames", "noErrorStatusFrames", "correctedStatusFrames",
                "failedStatusFrames"]


def one_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        values = list(csv.DictReader(handle))
    if len(values) != 1: raise RuntimeError(f"expected one summary row: {path}")
    return values[0]


def write_dict_rows(path: Path, values: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0])); writer.writeheader(); writer.writerows(values)


def expect_failure(command: list[str], repo: Path, label: str) -> dict[str, object]:
    completed = subprocess.run(command, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode == 0:
        raise SystemExit(f"negative test unexpectedly passed: {label}")
    return {"test": label, "status": "PASS_EXPECTED_REJECTION", "returnCode": completed.returncode,
            "message": completed.stderr.strip().replace("\n", " | ")[:300]}


def run_bch14(args: argparse.Namespace, repo: Path, build: Path, results: Path) -> None:
    executable = build / "bch_awgn_runner.exe"
    merge_script = repo / "Task/BCH/simulation/scripts/merge_bch_shards.py"
    trial = results / "formal_trial"
    if trial.exists(): shutil.rmtree(trial)
    trial.mkdir(parents=True)
    recommendations_path = repo / "Task/BCH/simulation/stages/bch13_awgn_prescan/prescan_case_recommendations.csv"
    recommendations = {row["caseName"]: row for row in csv.DictReader(recommendations_path.open(newline="", encoding="utf-8"))}
    pools = results / "frame_pools"
    manifests = {200: ensure_pool(repo, pools / "formal_trial_k200", 200, 20000, args.payload_seed),
                 300: ensure_pool(repo, pools / "formal_trial_k300", 300, 20000, args.payload_seed)}
    print("[4/6] BCH-14 execution plan")
    print("Cases: 4 | LOW/MID/HIGH points: 12 | minFrames: 5000 | target FE: 100 | maxFrames: 20000")
    print(f"Resume checks: 4 x 6000 frames | shard checks: 4 x 3 shards | Output: {trial}")

    trial_points: list[Path] = []
    for case in CASES:
        payload = 200 if case.endswith("200") else 300
        rec = recommendations[case]
        for label, field in [("LOW", "waterfallLowDb"), ("MID", "waterfallMidDb"), ("HIGH", "waterfallHighDb")]:
            snr = float(rec[field]); snr_index = int(round(snr * 10.0))
            point = trial / "points" / f"{case.lower().replace('-', '_')}_{label.lower()}"
            checkpoint = trial / "checkpoints" / f"{case.lower().replace('-', '_')}_{label.lower()}.json"
            execute_point(repo, executable, point, "BCH14", case, snr, snr_index, 20000, args.global_seed,
                          manifests[payload], args.progress, args.progress_refresh_seconds, False,
                          extra_args=["--logical-frame-count", "20000", "--min-frames", "5000",
                                      "--target-frame-errors", "100", "--max-frames", "20000",
                                      "--checkpoint", str(checkpoint), "--checkpoint-interval", "1000"])
            row = one_row(point / "summary.csv")
            if row["stopReason"] not in {"TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"}:
                raise SystemExit("BLOCKED_BCH14_INVALID_STOP_REASON")
            if int(row["processedFrames"]) < 5000:
                raise SystemExit("BCH-14 stopped before minimum frames")
            trial_points.append(point)
    combine_files(trial_points, "summary.csv", trial / "formal_trial_summary.csv")

    resume_rows: list[dict[str, object]] = []
    shard_rows: list[dict[str, object]] = []
    checkpoint_rows: list[dict[str, object]] = []
    negative_rows: list[dict[str, object]] = []
    extra_progress: list[Path] = []
    for case in CASES:
        payload = 200 if case.endswith("200") else 300
        snr = float(recommendations[case]["waterfallMidDb"]); snr_index = int(round(snr * 10.0))
        prefix = case.lower().replace('-', '_')
        continuous = trial / "resume" / prefix / "continuous"
        partial = trial / "resume" / prefix / "partial"
        resumed = trial / "resume" / prefix / "resumed"
        checkpoint = trial / "resume" / prefix / "state.json"
        common_extra = ["--logical-frame-count", "6000"]
        execute_point(repo, executable, continuous, "BCH14_RESUME", case, snr, snr_index, 6000, args.global_seed,
                      manifests[payload], False, args.progress_refresh_seconds, True, extra_args=common_extra)
        execute_point(repo, executable, partial, "BCH14_RESUME", case, snr, snr_index, 6000, args.global_seed,
                      manifests[payload], False, args.progress_refresh_seconds, True,
                      extra_args=common_extra + ["--checkpoint", str(checkpoint), "--checkpoint-interval", "1000",
                                                 "--interrupt-after-frames", "2500"])
        execute_point(repo, executable, resumed, "BCH14_RESUME", case, snr, snr_index, 6000, args.global_seed,
                      manifests[payload], False, args.progress_refresh_seconds, True,
                      extra_args=common_extra + ["--checkpoint", str(checkpoint), "--checkpoint-interval", "1000", "--resume"])
        continuous_row = one_row(continuous / "summary.csv"); resumed_row = one_row(resumed / "summary.csv")
        counter_mismatches = sum(continuous_row[field] != resumed_row[field] for field in RAW_COUNTERS)
        continuous_detail = {row["frameIndex"]: row for row in csv.DictReader((continuous / "frame_detail.csv").open(newline="", encoding="utf-8"))}
        resumed_detail = list(csv.DictReader((partial / "frame_detail.csv").open(newline="", encoding="utf-8"))) + list(csv.DictReader((resumed / "frame_detail.csv").open(newline="", encoding="utf-8")))
        noise_mismatches = sum(continuous_detail[row["frameIndex"]]["noiseHash"] != row["noiseHash"] for row in resumed_detail)
        if counter_mismatches or noise_mismatches or len(resumed_detail) != 6000:
            raise SystemExit("BLOCKED_BCH14_CHECKPOINT_RESUME_MISMATCH")
        resume_rows.append({"caseName": case, "ebn0Db": snr, "continuousFrames": continuous_row["processedFrames"],
                            "resumedFrames": resumed_row["processedFrames"], "counterMismatches": counter_mismatches,
                            "noiseHashMismatches": noise_mismatches, "checkpointCount": resumed_row["checkpointCount"], "status": "PASS"})
        state = __import__("json").loads(checkpoint.read_text(encoding="utf-8"))
        required_fields = ["schemaVersion", "configHash", "nextFrameIndex", "bitErrors", "frameErrors",
                           "reportedSuccessFrames", "miscorrectedFrames", "decoderFailureFrames", "noisePolicyVersion",
                           "globalSeed", "shardIndex", "shardCount", "checkpointCount", "timestamp"]
        missing = [field for field in required_fields if field not in state]
        checkpoint_rows.append({"caseName": case, "checkpointPath": str(checkpoint.relative_to(trial)),
                                "nextFrameIndex": state["nextFrameIndex"], "missingRequiredFields": ";".join(missing),
                                "temporaryFileExists": checkpoint.with_suffix(checkpoint.suffix + ".tmp").exists(),
                                "status": "PASS" if not missing and not checkpoint.with_suffix(checkpoint.suffix + ".tmp").exists() else "FAIL"})
        bad_seed_command = [str(executable), "--stage", "BCH14_RESUME", "--case", case, "--ebn0-db", str(snr),
                            "--snr-index", str(snr_index), "--frame-start", "0", "--frame-count", "6000",
                            "--logical-frame-count", "6000", "--global-seed", str(args.global_seed + 1),
                            "--frame-pool-manifest", str(manifests[payload]), "--output-dir", str(trial / "negative" / prefix / "bad_seed"),
                            "--checkpoint", str(checkpoint), "--checkpoint-interval", "1000", "--resume", "--no-progress"]
        negative_rows.append(expect_failure(bad_seed_command, repo, f"{case}_resume_config_hash_seed_mismatch"))
        extra_progress.extend([continuous, partial, resumed])

        shard_summaries: list[Path] = []
        for shard_index in range(3):
            shard = trial / "shards" / prefix / f"shard{shard_index}"
            execute_point(repo, executable, shard, "BCH14_SHARD", case, snr, snr_index, 2000, args.global_seed,
                          manifests[payload], False, args.progress_refresh_seconds, False, frame_start=shard_index * 2000,
                          extra_args=["--logical-frame-count", "6000", "--shard-index", str(shard_index), "--shard-count", "3"])
            shard_summaries.append(shard / "summary.csv"); extra_progress.append(shard)
        merged = trial / "shards" / prefix / "merged.csv"
        merge_command = [sys.executable, str(merge_script), "--inputs", *map(str, shard_summaries), "--output", str(merged),
                         "--expected-frame-count", "6000", "--expected-shard-count", "3"]
        run(merge_command, repo)
        merged_row = one_row(merged)
        shard_mismatches = sum(continuous_row[field] != merged_row[field] for field in RAW_COUNTERS)
        if shard_mismatches: raise SystemExit("BLOCKED_BCH14_SHARD_MERGE_MISMATCH")
        shard_rows.append({"caseName": case, "ebn0Db": snr, "continuousFrames": continuous_row["processedFrames"],
                           "mergedFrames": merged_row["processedFrames"], "loadedShards": merged_row["loadedShards"],
                           "counterMismatches": shard_mismatches, "duplicateFrames": 0, "missingFrames": 0, "status": "PASS"})

        if case == CASES[0]:
            duplicate = merge_command.copy(); duplicate[duplicate.index(str(shard_summaries[1]))] = str(shard_summaries[0])
            negative_rows.append(expect_failure(duplicate, repo, "duplicate_shard_rejection"))
            missing = [sys.executable, str(merge_script), "--inputs", str(shard_summaries[0]), str(shard_summaries[2]),
                       "--output", str(trial / "negative/missing.csv"), "--expected-frame-count", "6000", "--expected-shard-count", "3"]
            negative_rows.append(expect_failure(missing, repo, "missing_shard_rejection"))
            mutated_dir = trial / "negative"; mutated_dir.mkdir(exist_ok=True)
            mutated = mutated_dir / "overlap_summary.csv"; row = one_row(shard_summaries[1]); row["frameStart"] = "1999"
            with mutated.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
            overlap = [sys.executable, str(merge_script), "--inputs", str(shard_summaries[0]), str(mutated), str(shard_summaries[2]),
                       "--output", str(trial / "negative/overlap.csv"), "--expected-frame-count", "6000", "--expected-shard-count", "3"]
            negative_rows.append(expect_failure(overlap, repo, "overlap_rejection"))
            mutations = {"caseName": "BCH-B200", "ebn0Db": str(snr + 0.1),
                         "globalSeed": str(args.global_seed + 1), "noisePolicyVersion": "2",
                         "configHash": "0" * 64}
            for field, replacement in mutations.items():
                identity_mutated = mutated_dir / f"{field}_summary.csv"
                row = one_row(shard_summaries[1]); row[field] = replacement
                with identity_mutated.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
                command = [sys.executable, str(merge_script), "--inputs", str(shard_summaries[0]), str(identity_mutated), str(shard_summaries[2]),
                           "--output", str(trial / "negative" / f"{field}.csv"), "--expected-frame-count", "6000", "--expected-shard-count", "3"]
                negative_rows.append(expect_failure(command, repo, f"{field}_mismatch_rejection"))

    write_dict_rows(trial / "resume_audit.csv", resume_rows)
    write_dict_rows(trial / "shard_merge_audit.csv", shard_rows)
    write_dict_rows(trial / "checkpoint_audit.csv", checkpoint_rows)
    write_dict_rows(trial / "negative_test_results.csv", negative_rows)
    combine_jsonl(trial_points + extra_progress, "progress.jsonl", trial / "progress.jsonl")
    if any(row["status"] != "PASS" for row in checkpoint_rows):
        raise SystemExit("BLOCKED_BCH14_CHECKPOINT_RESUME_MISMATCH")
    print("PASS_BCH14_FORMAL_INFRASTRUCTURE_TRIAL casePoints=12 resumeCases=4 shardCases=4")


def inclusive_grid(minimum: float, maximum: float, step: float) -> list[float]:
    values: list[float] = []; current = minimum
    while current <= maximum + 1e-9:
        values.append(round(current, 10)); current += step
    if abs(values[-1] - maximum) > 1e-9: values.append(round(maximum, 10))
    return values


def wilson_interval(errors: int, frames: int) -> tuple[float, float]:
    z = 1.959963984540054; p = errors / frames; denominator = 1.0 + z * z / frames
    center = (p + z * z / (2.0 * frames)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / frames + z * z / (4.0 * frames * frames)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def run_bch15(args: argparse.Namespace, repo: Path, build: Path, results: Path) -> None:
    executable = build / "bch_awgn_runner.exe"; formal = results / "formal"
    if formal.exists(): shutil.rmtree(formal)
    formal.mkdir(parents=True)
    recommendation_path = repo / "Task/BCH/simulation/stages/bch13_awgn_prescan/prescan_case_recommendations.csv"
    recommendations = {row["caseName"]: row for row in csv.DictReader(recommendation_path.open(newline="", encoding="utf-8"))}
    grids = {case: inclusive_grid(float(recommendations[case]["recommendedFormalMinDb"]),
                                  float(recommendations[case]["recommendedFormalMaxDb"]),
                                  float(recommendations[case]["recommendedFormalStepDb"])) for case in CASES}
    grid_rows = [{"caseName": case, "ebn0Db": snr, "gridIndex": index,
                  "sourceMinDb": recommendations[case]["recommendedFormalMinDb"],
                  "sourceMaxDb": recommendations[case]["recommendedFormalMaxDb"],
                  "sourceStepDb": recommendations[case]["recommendedFormalStepDb"]}
                 for case in CASES for index, snr in enumerate(grids[case])]
    write_dict_rows(formal / "frozen_formal_grid.csv", grid_rows)
    case_points = sum(len(values) for values in grids.values())
    print("[5/6] BCH-15 execution plan")
    print(f"Cases: 4 | case-points: {case_points} | minFrames: 5000 | target FE: 200 | maxFrames: 50000")
    print(f"Minimum frames: {case_points * 5000} | maximum frames: {case_points * 50000} | checkpoint every: 2000")
    print(f"Progress: {'enabled' if args.progress else 'disabled'} refresh={args.progress_refresh_seconds}s | Output: {formal}")
    pools = results / "frame_pools"
    manifests = {200: ensure_pool(repo, pools / "formal_k200", 200, 50000, args.payload_seed),
                 300: ensure_pool(repo, pools / "formal_k300", 300, 50000, args.payload_seed)}
    points: list[Path] = []; completed = 0
    for case in CASES:
        payload = 200 if case.endswith("200") else 300
        for grid_index, snr in enumerate(grids[case]):
            snr_index = int(round(snr * 10.0)); point = formal / "points" / f"{case.lower().replace('-', '_')}_{grid_index:02d}"
            checkpoint = formal / "checkpoints" / f"{case.lower().replace('-', '_')}_{grid_index:02d}.json"
            execute_point(repo, executable, point, "BCH15", case, snr, snr_index, 50000, args.global_seed,
                          manifests[payload], args.progress, args.progress_refresh_seconds, False,
                          extra_args=["--logical-frame-count", "50000", "--min-frames", "5000",
                                      "--target-frame-errors", "200", "--max-frames", "50000",
                                      "--checkpoint", str(checkpoint), "--checkpoint-interval", "2000"])
            points.append(point); completed += 1; print(f"\r[BCH-15] case-points {completed}/{case_points}", end="", flush=True)
    print(); combine_files(points, "summary.csv", formal / "formal_summary_raw.csv"); combine_jsonl(points, "progress.jsonl", formal / "progress.jsonl")
    raw_rows = list(csv.DictReader((formal / "formal_summary_raw.csv").open(newline="", encoding="utf-8")))
    git_commit = run(["git", "rev-parse", "HEAD"], repo, capture=True).stdout.strip(); output_rows: list[dict[str, object]] = []
    for row in raw_rows:
        errors = int(row["decodedFrameErrors"]); frames = int(row["processedFrames"]); lower, upper = wilson_interval(errors, frames)
        enriched: dict[str, object] = dict(row); enriched.update({"runId": f"bch15-seed{args.global_seed}",
            "ferCiLower95": f"{lower:.17g}", "ferCiUpper95": f"{upper:.17g}",
            "ferUpper95RuleOfThree": f"{3.0 / frames:.17g}" if errors == 0 else "",
            "gitCommit": git_commit})
        output_rows.append(enriched)
    write_dict_rows(formal / "formal_summary.csv", output_rows)
    expected = {(row["caseName"], float(row["ebn0Db"])) for row in grid_rows}; actual = {(row["caseName"], float(row["ebn0Db"])) for row in output_rows}
    if expected != actual or len(output_rows) != case_points: raise SystemExit("BLOCKED_BCH15_FORMAL_POINT_INCOMPLETE")
    numeric = ["BER", "FER", "trueSuccessRate", "reportedSuccessRate", "miscorrectionRate", "decoderFailureRate",
               "avgEncodeTimeUs", "avgDecodeTimeUs", "p50DecodeTimeUs", "p95DecodeTimeUs", "p99DecodeTimeUs", "maxDecodeTimeUs",
               "ferCiLower95", "ferCiUpper95"]
    for row in output_rows:
        if row["stopReason"] not in {"TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"}: raise SystemExit("BLOCKED_BCH15_INVALID_STOP_REASON")
        if any(not math.isfinite(float(row[field])) for field in numeric): raise SystemExit("BLOCKED_BCH15_METRIC_INCONSISTENCY")
        frames = int(row["processedFrames"])
        if int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != frames: raise SystemExit("BLOCKED_BCH15_METRIC_INCONSISTENCY")
        if int(row["reportedSuccessFrames"]) + int(row["decoderFailureFrames"]) != frames: raise SystemExit("BLOCKED_BCH15_METRIC_INCONSISTENCY")
    checkpoint_rows = [{"path": str(path.relative_to(formal)).replace("\\", "/"), "bytes": path.stat().st_size,
                        "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest()} for path in sorted((formal / "checkpoints").glob("*.json"))]
    write_dict_rows(formal / "checkpoint_summary.csv", checkpoint_rows)
    run([sys.executable, str(repo / "Task/BCH/simulation/scripts/plot_bch_formal.py"),
         "--summary", str(formal / "formal_summary.csv"), "--output-dir", str(formal)], repo)
    print(f"PASS_BCH15_AWGN_FORMAL casePoints={case_points} frames={sum(int(row['processedFrames']) for row in output_rows)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["bch11", "bch12", "bch13", "bch14", "bch15", "bch16"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--global-seed", type=int, default=2026072201)
    parser.add_argument("--payload-seed", type=int, default=2026072001)
    parser.add_argument("--progress", dest="progress", action="store_true", default=True)
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.add_argument("--progress-refresh-seconds", type=float, default=0.2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--checkpoint-interval", type=int, default=2000)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--matlab-command", default="matlab")
    parser.add_argument("--skip-matlab", action="store_true")
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    build = (args.build_dir or repo / "Task/BCH/simulation/build/current").resolve()
    results = (args.results_dir or repo / "Task/BCH/simulation/results").resolve()
    if args.progress_refresh_seconds <= 0.0:
        raise SystemExit("progress refresh must be positive")
    if args.dry_run:
        print("BCH Group 4 plan: BCH-11 -> BCH-12 -> BCH-13 -> BCH-14 -> BCH-15 -> BCH-16")
        print("BCH-12: 4 cases, 5 SNR points, 200 frames/point, 4000 maximum frames")
        print("BCH-13: 4 cases, 21 SNR points, 2000 frames/point, 168000 maximum frames")
        print("BCH-14: 12 adaptive trial points plus 4 resume and 4 three-shard equivalence checks")
        print("BCH-15: formal grids read from BCH-13 recommendations, 5000/200/50000 stop rule")
        print(f"Output: {results}")
        return 0
    selected = args.stage or ("bch12" if not args.all else "all")
    if selected in {"bch11"}:
        raise SystemExit("BCH-11 is executed by CTest; use the documented BCH-11 command")
    if selected in {"bch12", "all"}:
        run_bch12(args, repo, build, results)
    if selected in {"bch13", "all"}:
        run_bch13(args, repo, build, results)
    if selected in {"bch14", "all"}:
        run_bch14(args, repo, build, results)
    if selected in {"bch15", "all"}:
        run_bch15(args, repo, build, results)
    if selected in {"bch16"}:
        raise SystemExit("requested stage is not implemented in the current ordered functional range")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
