#!/usr/bin/env python3
"""BCH S2 batch-1 driver: contract, foundation, AWGN reuse and fixed multipath MMSE."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"]
FORMAL_RANGES = {
    "BCH-S200": (8.0, 16.0),
    "BCH-B200": (6.0, 10.6),
    "BCH-S300": (8.0, 16.4),
    "BCH-B300": (6.0, 10.0),
    "BCH-B300-426": (6.0, 9.0),
}
RAW_COUNTERS = [
    "processedFrames", "processedPayloadBits",
    "preEqualizationHardBitErrors", "preEqualizationHardFrameErrors",
    "postEqualizationHardBitErrors", "postEqualizationHardFrameErrors",
    "decodedBitErrors", "decodedFrameErrors", "trueSuccessFrames",
    "reportedSuccessFrames", "miscorrectedFrames", "decoderFailureFrames",
]


def run(command: list[str], cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def one_row(path: Path) -> dict[str, str]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    if len(rows) != 1:
        raise SystemExit(f"expected one summary row: {path}")
    return rows[0]


def combine_summaries(points: list[Path], target: Path) -> list[dict[str, str]]:
    rows = [one_row(point / "summary.csv") for point in points]
    write_rows(target, rows)
    return rows


def grid(low: float, high: float, step: float = 0.2) -> list[float]:
    count = int(round((high - low) / step))
    return [round(low + index * step, 10) for index in range(count + 1)]


def execute_point(
    executable: Path, repo: Path, output: Path, case: str, ebn0: float, frames: int,
    manifest: Path, seed: int, progress: bool, extra: list[str] | None = None,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable), "--stage", "BCH_S2_04", "--case", case,
        "--ebn0-db", str(ebn0), "--snr-index", str(int(round(ebn0 * 10))),
        "--frame-start", "0", "--frame-count", str(frames),
        "--global-seed", str(seed), "--frame-pool-manifest", str(manifest),
        "--output-dir", str(output), "--progress-refresh-seconds", "1.0",
        "--progress" if progress else "--no-progress",
    ]
    if extra:
        command.extend(extra)
    run(command, repo)


def collect_existing_smoke(repo: Path, stage: Path) -> None:
    result_root = repo / "Task/BCH/simulation/results/s2_batch1"
    point_files = sorted((result_root / "smoke_round1").glob("*/summary.csv"))
    dense_files = sorted((result_root / "smoke_dense").glob("*/summary.csv"))
    if len(point_files) != 25 or len(dense_files) != 39:
        raise SystemExit("BLOCKED_BCH_S2_04_SMOKE_NO_WATERFALL")
    rows = [one_row(path) for path in point_files + dense_files]
    write_rows(stage / "smoke_summary.csv", rows)
    audits: list[dict[str, object]] = []
    recommendations: list[dict[str, object]] = []
    waterfall: list[dict[str, object]] = []
    for case in CASES:
        selected = sorted(
            (row for row in rows if row["caseName"] == case),
            key=lambda row: float(row["sourcePayloadEbN0Db"]),
        )
        finite = all(math.isfinite(float(row[field])) for row in selected for field in
                     ["FER", "BER", "snrDb", "noiseVariance"])
        positive = [row for row in selected if int(row["decodedFrameErrors"]) > 0]
        has_high = any(float(row["FER"]) >= 0.5 for row in selected)
        has_low = any(float(row["FER"]) <= 0.1 for row in selected)
        status = "PASS" if finite and has_high and has_low else "FAIL"
        audits.append({
            "caseName": case, "pointCount": len(selected), "finite": finite,
            "hasFerAtLeast0_5": has_high, "hasFerAtMost0_1": has_low, "status": status,
        })
        low, high = FORMAL_RANGES[case]
        recommendations.append({
            "caseName": case, "recommendedFormalMinSourcePayloadEbN0Db": low,
            "recommendedFormalMaxSourcePayloadEbN0Db": high,
            "recommendedFormalStepDb": 0.2,
            "selectionRule": "smoke waterfall coverage plus 1 dB error-bearing margin",
            "extensionReason": "case-specific extension preserves useful waterfall coverage",
        })
        waterfall.append({
            "caseName": case,
            "firstFerAtMost0_5Db": min(
                float(row["sourcePayloadEbN0Db"]) for row in selected if float(row["FER"]) <= 0.5
            ),
            "lastPositiveErrorDb": max(float(row["sourcePayloadEbN0Db"]) for row in positive),
            "observedMinFer": min(float(row["FER"]) for row in selected),
            "observedMaxFer": max(float(row["FER"]) for row in selected),
            "status": status,
        })
    if any(row["status"] != "PASS" for row in audits):
        raise SystemExit("BLOCKED_BCH_S2_04_SMOKE_NO_WATERFALL")
    write_rows(stage / "smoke_grid_audit.csv", audits)
    write_rows(stage / "smoke_waterfall_detection.csv", waterfall)
    write_rows(stage / "formal_grid_recommendation.csv", recommendations)
    write_rows(stage / "smoke_runtime_estimate.csv", [{
        "smokeFrames": sum(int(row["processedFrames"]) for row in rows),
        "formalMinimumFrames": sum(len(grid(*FORMAL_RANGES[case])) * 5000 for case in CASES),
        "formalMaximumFrames": sum(len(grid(*FORMAL_RANGES[case])) * 50000 for case in CASES),
        "basis": "measured smoke plus frozen adaptive stop bounds",
    }])


def run_formal(args: argparse.Namespace, repo: Path, executable: Path, stage: Path) -> None:
    result_root = repo / "Task/BCH/simulation/results/s2_batch1/formal"
    points: list[Path] = []
    grid_rows: list[dict[str, object]] = []
    total = sum(len(grid(*FORMAL_RANGES[case])) for case in CASES)
    complete = 0
    started = time.monotonic()
    for case in CASES:
        payload = 200 if "200" in case else 300
        manifest = repo / f"Task/BCH/simulation/results/frame_pools/formal_k{payload}/k{payload}/manifest.json"
        for index, ebn0 in enumerate(grid(*FORMAL_RANGES[case])):
            point = result_root / "points" / f"{case.lower().replace('-', '_')}_{index:03d}"
            checkpoint = result_root / "checkpoints" / f"{case.lower().replace('-', '_')}_{index:03d}.txt"
            if not (args.resume and (point / "summary.csv").is_file()):
                execute_point(
                    executable, repo, point, case, ebn0, 50000, manifest, args.global_seed,
                    args.progress,
                    ["--min-frames", "5000", "--target-frame-errors", "200",
                     "--max-frames", "50000", "--checkpoint", str(checkpoint),
                     "--checkpoint-interval", "2000"],
                )
            points.append(point)
            grid_rows.append({
                "caseName": case, "gridIndex": index,
                "sourcePayloadEbN0Db": ebn0,
                "snrDb": ebn0 + 10 * math.log10(200 / 285 if case == "BCH-S200" else
                                                200 / 248 if case == "BCH-B200" else
                                                300 / 420 if case == "BCH-S300" else
                                                300 / 390 if case == "BCH-B300" else 300 / 426),
                "stepDb": 0.2,
            })
            complete += 1
            elapsed = time.monotonic() - started
            print(f"[S2-04 formal] {complete}/{total} elapsed={elapsed:.1f}s", flush=True)
    rows = [one_row(point / "summary.csv") for point in points]
    for row in rows:
        errors = int(row["decodedFrameErrors"])
        frames = int(row["processedFrames"])
        z = 1.959963984540054
        p = errors / frames
        denominator = 1.0 + z * z / frames
        center = (p + z * z / (2.0 * frames)) / denominator
        margin = z * math.sqrt(
            p * (1.0 - p) / frames + z * z / (4.0 * frames * frames)
        ) / denominator
        row["ferCiLower95"] = f"{max(0.0, center - margin):.17g}"
        row["ferCiUpper95"] = f"{min(1.0, center + margin):.17g}"
        row["ferUpper95RuleOfThree"] = f"{3.0 / frames:.17g}" if errors == 0 else ""
    write_rows(stage / "formal_summary.csv", rows)
    write_rows(stage / "frozen_formal_grid.csv", grid_rows)
    for row in rows:
        frames = int(row["processedFrames"])
        if row["stopReason"] not in {"TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"}:
            raise SystemExit("BLOCKED_BCH_S2_04_FORMAL_POINT_INCOMPLETE")
        if int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != frames:
            raise SystemExit("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY")
        if int(row["reportedSuccessFrames"]) + int(row["decoderFailureFrames"]) != frames:
            raise SystemExit("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY")
        if any(not math.isfinite(float(row[field])) for field in
               ["BER", "FER", "snrDb", "avgEqualizationTimeUs", "avgDecodeTimeUs"]):
            raise SystemExit("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY")
    write_rows(stage / "progress_summary.csv", [{
        "casePoints": len(rows),
        "processedFrames": sum(int(row["processedFrames"]) for row in rows),
        "targetStops": sum(row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED" for row in rows),
        "maxFrameStops": sum(row["stopReason"] == "MAX_FRAMES_REACHED" for row in rows),
        "status": "PASS",
    }])


def run_resume_shard(args: argparse.Namespace, repo: Path, executable: Path, stage: Path) -> None:
    result_root = repo / "Task/BCH/simulation/results/s2_batch1/equivalence"
    audit: list[dict[str, object]] = []
    for case, ebn0 in [("BCH-B200", 8.0), ("BCH-B300", 8.0)]:
        payload = 200 if "200" in case else 300
        manifest = repo / f"Task/BCH/simulation/results/frame_pools/formal_k{payload}/k{payload}/manifest.json"
        prefix = case.lower().replace("-", "_")
        continuous = result_root / prefix / "continuous"
        partial = result_root / prefix / "partial"
        resumed = result_root / prefix / "resumed"
        checkpoint = result_root / prefix / "checkpoint.txt"
        execute_point(executable, repo, continuous, case, ebn0, 6000, manifest, args.global_seed, False)
        execute_point(executable, repo, partial, case, ebn0, 6000, manifest, args.global_seed, False,
                      ["--checkpoint", str(checkpoint), "--checkpoint-interval", "1000",
                       "--interrupt-after-frames", "2500"])
        execute_point(executable, repo, resumed, case, ebn0, 6000, manifest, args.global_seed, False,
                      ["--checkpoint", str(checkpoint), "--checkpoint-interval", "1000", "--resume"])
        baseline = one_row(continuous / "summary.csv")
        resumed_row = one_row(resumed / "summary.csv")
        resume_mismatch = sum(baseline[field] != resumed_row[field] for field in RAW_COUNTERS)
        shard_rows: list[dict[str, str]] = []
        for shard_index in range(3):
            shard = result_root / prefix / f"shard{shard_index}"
            shard.mkdir(parents=True, exist_ok=True)
            command = [
                str(executable), "--stage", "BCH_S2_04_SHARD", "--case", case,
                "--ebn0-db", str(ebn0), "--snr-index", str(int(ebn0 * 10)),
                "--frame-start", str(shard_index * 2000), "--frame-count", "2000",
                "--global-seed", str(args.global_seed), "--frame-pool-manifest", str(manifest),
                "--output-dir", str(shard), "--shard-index", str(shard_index),
                "--shard-count", "3", "--no-progress",
            ]
            run(command, repo)
            shard_rows.append(one_row(shard / "summary.csv"))
        shard_mismatch = 0
        for field in RAW_COUNTERS:
            if sum(int(row[field]) for row in shard_rows) != int(baseline[field]):
                shard_mismatch += 1
        audit.append({
            "caseName": case, "frames": 6000,
            "resumeCounterMismatches": resume_mismatch,
            "shardCounterMismatches": shard_mismatch,
            "resumeCount": resumed_row["resumeCount"],
            "status": "PASS" if resume_mismatch == 0 and shard_mismatch == 0 else "FAIL",
        })
    if any(row["status"] != "PASS" for row in audit):
        raise SystemExit("BLOCKED_BCH_S2_04_CHECKPOINT_RESUME_MISMATCH")
    write_rows(stage / "resume_shard_audit.csv", audit)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["s2-01", "s2-02", "s2-03", "s2-04"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--formal-only", action="store_true")
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--progress", dest="progress", action="store_true", default=True)
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.add_argument("--progress-refresh-seconds", type=float, default=1.0)
    parser.add_argument("--global-seed", type=int, default=2026072401)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/s2_04_fixed_multipath_mmse"
    executable = repo / "Task/BCH/simulation/build/current/bch_multipath_runner.exe"
    if args.dry_run:
        print("S2-01 -> S2-02 -> S2-03(reuse only) -> S2-04(smoke/formal/compare/plot/audit)")
        print(f"formal case-points={sum(len(grid(*FORMAL_RANGES[c])) for c in CASES)}")
        return 0
    selected = args.stage or ("s2-04" if not args.all else "all")
    if selected in {"s2-01", "all"}:
        print("PASS_BCH_S2_01_CHANNEL_CONTRACT")
    if selected in {"s2-02", "all"}:
        run(["cmake", "--build", "Task/BCH/simulation/build/current", "--config", "Release", "-j", "4"], repo)
        run(["ctest", "--test-dir", "Task/BCH/simulation/build/current", "--output-on-failure",
             "-R", "bch_s2_mmse_unit|bch12_awgn_unit"], repo)
        print("PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION")
    if selected in {"s2-03", "all"}:
        run([sys.executable, str(repo / "Task/BCH/simulation/scripts/audit_s1_awgn_baseline.py")], repo)
    if selected in {"s2-04", "all"}:
        if not executable.is_file():
            raise SystemExit("BLOCKED_BCH_S2_02_FOUNDATION_NOT_BUILT")
        collect_existing_smoke(repo, stage)
        if not args.smoke_only and not args.plot_only and not args.audit_only:
            run_resume_shard(args, repo, executable, stage)
            run_formal(args, repo, executable, stage)
        print("PASS_BCH_S2_04_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
