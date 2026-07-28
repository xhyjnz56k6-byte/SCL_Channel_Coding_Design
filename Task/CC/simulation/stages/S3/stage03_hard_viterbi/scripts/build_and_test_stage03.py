#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    build = stage / "build"
    results = stage / "results"
    if "--clean" in sys.argv and build.exists():
        shutil.rmtree(build)
    results.mkdir(parents=True, exist_ok=True)
    run([
        "cmake", "-S", str(stage), "-B", str(build), "-G", "MinGW Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
    ], stage)
    run(["cmake", "--build", str(build), "--parallel"], stage)
    run(["ctest", "--test-dir", str(build), "--output-on-failure"], stage)
    executable = build / "stage03_hard_viterbi_tests.exe"
    vectors = results / "stage03_hard_viterbi_cpp_matlab_vectors.csv"
    run([str(executable), str(vectors)], stage)

    comparison = results / "stage03_hard_viterbi_matlab_comparison.csv"
    summary = results / "stage03_hard_viterbi_test_summary.csv"
    with summary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["check", "status"])
        writer.writerow(["release_build", "PASS"])
        writer.writerow(["ctest", "PASS"])
        writer.writerow(["noiseless_random_100", "PASS"])
        writer.writerow(["invalid_input_negative", "PASS"])
        if comparison.is_file():
            with comparison.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            passed = len(rows) == 5 and all(
                row["status"] == "PASS"
                and int(row["codecInputMismatch"]) == 0
                and int(row["payloadMismatch"]) == 0
                for row in rows
            )
            if not passed:
                raise RuntimeError("MATLAB hard Viterbi comparison failed")
            writer.writerow(["matlab_vitdec_vectors", "PASS"])
            writer.writerow(["payload_mismatch", "0"])
            writer.writerow(["stage_gate", "PASS_STAGE03_CC_HARD_VITERBI"])
        else:
            writer.writerow(["stage_gate_before_matlab", "PASS_CPP"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
