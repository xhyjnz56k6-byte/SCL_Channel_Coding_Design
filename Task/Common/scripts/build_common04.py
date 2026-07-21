#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path


TESTS = [
    "test_common04_random_policy",
    "test_common04_gaussian_noise",
    "test_common04_modulation_awgn",
    "test_common04_metrics_control",
    "test_common04_checkpoint",
    "test_common04_integration",
]

SOURCES = [
    "src/random_policy.cpp",
    "src/gaussian_noise.cpp",
    "src/noise_pool.cpp",
    "src/modulation.cpp",
    "src/awgn_channel.cpp",
    "src/demodulation.cpp",
    "src/simulation_metrics.cpp",
    "src/simulation_control.cpp",
    "src/checkpoint.cpp",
    "src/result_schema.cpp",
    "src/simulation_pipeline.cpp",
]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out_dir = root / "Common" / "build" / "stage04"
    out_dir.mkdir(parents=True, exist_ok=True)
    for test in TESTS:
        exe = out_dir / f"{test}.exe"
        command = [
            "g++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(root / "Common" / "include"),
            str(root / "Common" / "tests" / "stage04" / f"{test}.cpp"),
            *(str(root / "Common" / source) for source in SOURCES),
            "-o",
            str(exe),
        ]
        print("RUN:", " ".join(command))
        completed = subprocess.run(command, cwd=root.parents[1])
        if completed.returncode != 0:
            print("COMMON-04 BUILD: FAIL")
            return completed.returncode
    print(f"COMMON-04 BUILD: PASS ({out_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
