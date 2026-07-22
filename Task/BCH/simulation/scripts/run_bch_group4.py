#!/usr/bin/env python3
"""Ordered BCH Group 4 build and experiment driver."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
import sys
from pathlib import Path


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300"]
SMOKE_SNR = [0.0, 2.0, 4.0, 6.0, 8.0]


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


def execute_point(repo: Path, executable: Path, output: Path, case: str, snr: float, snr_index: int,
                  frames: int, seed: int, manifest: Path, progress: bool, refresh: float,
                  detail: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    command = [str(executable), "--stage", "BCH12", "--case", case, "--ebn0-db", str(snr),
               "--snr-index", str(snr_index), "--frame-start", "0", "--frame-count", str(frames),
               "--global-seed", str(seed), "--frame-pool-manifest", str(manifest),
               "--output-dir", str(output), "--progress-refresh-seconds", str(refresh),
               "--progress" if progress else "--no-progress"]
    if detail:
        command.append("--detail")
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
            execute_point(repo, executable, point, case, snr, snr_index, 200, args.global_seed,
                          manifests[payload], args.progress, args.progress_refresh_seconds, True)
            execute_point(repo, executable, rerun, case, snr, snr_index, 200, args.global_seed,
                          manifests[payload], False, args.progress_refresh_seconds, True)
            points.append(point)
            reruns.append(rerun)
            completed += 1
            print(f"\r[BCH-12] case-points {completed}/20", end="", flush=True)
    print()
    combine_files(points, "summary.csv", smoke / "awgn_smoke_summary.csv")
    combine_files(points, "frame_detail.csv", smoke / "awgn_smoke_frame_detail.csv")
    combine_files(points, "progress.jsonl", smoke / "progress.jsonl")

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
        print(f"Output: {results}")
        return 0
    selected = args.stage or ("bch12" if not args.all else "all")
    if selected in {"bch11"}:
        raise SystemExit("BCH-11 is executed by CTest; use the documented BCH-11 command")
    if selected in {"bch12", "all"}:
        run_bch12(args, repo, build, results)
    if selected in {"bch13", "bch14", "bch15", "bch16"} or args.all:
        if selected != "bch12":
            raise SystemExit("requested stage is not implemented in the current ordered functional range")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
