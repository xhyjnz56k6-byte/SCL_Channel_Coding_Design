#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

from generate_common04_noise_pool import gaussian, word


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    output = root / "Task/Common/build/stage04/cpp_reference_runtime.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    runner = root / "Task/Common/build/stage04/common04_reference_runner.exe"
    completed = subprocess.run([str(runner), str(output)], cwd=root, text=True, capture_output=True)
    if completed.returncode:
        print(completed.stdout + completed.stderr, file=sys.stderr)
        return completed.returncode
    cpp = {row["field"]: float(row["value"]) for row in csv.DictReader(output.open(encoding="utf-8"))}
    sigma = math.sqrt(1.0 / (2.0 * (200.0 / 248.0) * 10.0 ** (2.0 / 10.0)))
    received = 1.0 + 0.5 * sigma
    expected = {
        "noiseWord0": float(word(2026072101, 0, 0, 0)), "noiseWord1": float(word(2026072101, 0, 0, 1)),
        "gaussian0": gaussian(2026072101, 0, 0, 0), "bpsk0": 1.0, "bpsk1": -1.0,
        "codeRate": 200.0 / 248.0, "sigma": sigma, "received": received, "llr": 2.0 * received / (sigma * sigma),
        "hardDecision": 0.0, "llrSignDecision": 0.0,
    }
    rows: list[dict[str, object]] = []
    mismatches = 0
    for field, python_value in expected.items():
        cpp_value = cpp[field]
        tolerance = 0.0 if field.startswith("noiseWord") or field.endswith("Decision") else 1e-12
        difference = abs(cpp_value - python_value)
        status = "PASS" if difference <= tolerance else "FAIL"
        mismatches += status == "FAIL"
        rows.append({"caseName": "frozen_reference", "field": field, "cppValue": cpp_value, "pythonValue": python_value,
                     "absDiff": difference, "tolerance": tolerance, "status": status})
    comparison = root / "Task/Common/build/stage04/cpp_python_comparison_runtime.csv"
    with comparison.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"COMMON-04 CPP/PYTHON REFERENCE: {'PASS' if mismatches == 0 else 'FAIL'}")
    print(f"mismatchCount={mismatches}")
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
