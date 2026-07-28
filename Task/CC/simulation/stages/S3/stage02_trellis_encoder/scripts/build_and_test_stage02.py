#!/usr/bin/env python3
"""Configure, build and test Stage02 without writing outside Task/CC."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    stage = Path(__file__).resolve().parents[1]
    build = stage / "build"
    results = stage / "results"
    if args.clean and build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    configure = [
        "cmake",
        "-S",
        str(stage),
        "-B",
        str(build),
        "-G",
        "MinGW Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    run(configure, stage)
    run(["cmake", "--build", str(build), "--config", "Release", "--parallel"], stage)
    run(["ctest", "--test-dir", str(build), "-C", "Release", "--output-on-failure"], stage)

    candidates = [
        build / "stage02_trellis_encoder_tests.exe",
        build / "Release" / "stage02_trellis_encoder_tests.exe",
        build / "stage02_trellis_encoder_tests",
    ]
    executable = next((item for item in candidates if item.is_file()), None)
    if executable is None:
        raise FileNotFoundError("Stage02 test executable not found")
    vector_path = results / "stage02_trellis_encoder_cpp_matlab_vectors.csv"
    run([str(executable), str(vector_path)], stage)

    summary = results / "stage02_trellis_encoder_test_summary.csv"
    with summary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["check", "status"])
        writer.writerow(["release_build", "PASS"])
        writer.writerow(["ctest", "PASS"])
        writer.writerow(["trellis_and_encoder_vectors", "PASS"])
        writer.writerow(["stage_gate_before_matlab", "PASS_CPP"])
    print("PASS_CPP_STAGE02_CC_TRELLIS_ENCODER")
    return 0


if __name__ == "__main__":
    sys.exit(main())
