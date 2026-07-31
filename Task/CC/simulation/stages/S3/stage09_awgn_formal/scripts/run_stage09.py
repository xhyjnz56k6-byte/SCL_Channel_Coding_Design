#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run(command: list[str], cwd: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != expected:
        raise RuntimeError(f"command returned {result.returncode}, expected {expected}")
    return result


def deterministic_row(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    timing = {
        "avgEncodeTime_us", "maxEncodeTime_us", "avgDecodeTime_us", "p95DecodeTime_us",
        "maxDecodeTime_us", "rawDecodeThroughput_Mbps", "successfulDecodeThroughput_Mbps",
    }
    return {key: value for key, value in row.items() if key not in timing}


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    build = stage / "build"
    runtime = stage / "runtime"
    results = stage / "results"
    if "--clean" in sys.argv:
        if build.exists():
            shutil.rmtree(build)
        if runtime.exists():
            shutil.rmtree(runtime)
    for output in (
        "stage09_awgn_formal_point_results.csv",
        "stage09_awgn_formal_plot_manifest.json",
        "formal_report.md",
    ):
        if (results / output).exists():
            raise RuntimeError(f"refusing to overwrite old formal output: {output}")
    runtime.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    run(
        ["cmake", "-S", str(stage), "-B", str(build), "-G", "MinGW Makefiles",
         "-DCMAKE_BUILD_TYPE=Release"],
        stage,
    )
    run(["cmake", "--build", str(build), "--parallel"], stage)
    executable = build / "stage09_awgn_formal_runner.exe"

    resume_dir = runtime / "resume_test"
    fresh_dir = runtime / "fresh_test"
    mismatch_dir = runtime / "mismatch_test"
    for directory in (resume_dir, fresh_dir, mismatch_dir):
        directory.mkdir()
    common = [
        "--unit-index", "0", "--min-frames", "200", "--target-frame-errors", "100000",
        "--max-frames", "400", "--checkpoint-interval", "100",
    ]
    run([str(executable), str(resume_dir), *common, "--interrupt-after-checkpoints", "1"], stage, 75)
    run([str(executable), str(resume_dir), *common, "--resume"], stage)
    run([str(executable), str(fresh_dir), *common], stage)
    if deterministic_row(resume_dir / "unit_000.csv") != deterministic_row(fresh_dir / "unit_000.csv"):
        raise RuntimeError("resume deterministic fields differ from continuous run")
    run([str(executable), str(mismatch_dir), *common, "--interrupt-after-checkpoints", "1"], stage, 75)
    mismatch = [
        "--unit-index", "0", "--min-frames", "201", "--target-frame-errors", "100000",
        "--max-frames", "400", "--checkpoint-interval", "100", "--resume",
    ]
    result = subprocess.run([str(executable), str(mismatch_dir), *mismatch], cwd=stage)
    if result.returncode == 0:
        raise RuntimeError("mismatched checkpoint configuration was accepted")

    formal_dir = runtime / "formal_v2"
    formal_dir.mkdir()
    processes: list[subprocess.Popen[str]] = []
    for shard in range(2):
        command = [
            str(executable), str(formal_dir), "--shard-index", str(shard), "--shard-count", "2",
            "--min-frames", "5000", "--target-frame-errors", "200",
            "--max-frames", "50000", "--checkpoint-interval", "1000",
        ]
        print("+", " ".join(command), flush=True)
        processes.append(subprocess.Popen(command, cwd=stage, text=True))
    last_update = time.monotonic()
    while any(process.poll() is None for process in processes):
        time.sleep(2)
        if time.monotonic() - last_update >= 30:
            completed = len(list(formal_dir.glob("unit_*.csv")))
            checkpoints = len(list(formal_dir.glob("*.chk")))
            print(f"formal progress: {completed}/103 units, {checkpoints} checkpoints", flush=True)
            last_update = time.monotonic()
    failures = [process.returncode for process in processes if process.returncode != 0]
    if failures:
        raise RuntimeError(f"formal shard failure: {failures}")
    run([sys.executable, str(stage / "scripts" / "merge_and_plot_stage09.py"),
         str(formal_dir), str(results)], stage)
    print("PASS_STAGE09_CC_AWGN_FORMAL_DRIVER")
    return 0


if __name__ == "__main__":
    sys.exit(main())
