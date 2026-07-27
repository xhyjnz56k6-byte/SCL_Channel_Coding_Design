#!/usr/bin/env python3
"""Compare independent C++ and MATLAB convolution/MMSE outputs."""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


def vector(text: str) -> list[float]:
    return [] if not text else [float(value) for value in text.split(";")]


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    with (results / "stage07_multipath_validation_cpp_outputs.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        cpp = {row["vectorId"]: row for row in csv.DictReader(handle)}
    with (results / "stage07_multipath_validation_matlab_outputs.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        matlab = {row["vectorId"]: row for row in csv.DictReader(handle)}
    if cpp.keys() != matlab.keys():
        raise RuntimeError("BLOCKED_STAGE07_VECTOR_ID_MISMATCH")

    rows: list[dict[str, object]] = []
    max_continuous = 0.0
    hard_mismatches = 0
    for vector_id in cpp:
        left, right = cpp[vector_id], matlab[vector_id]
        if int(left["outputLength"]) != int(right["outputLength"]):
            raise RuntimeError(f"BLOCKED_STAGE07_OUTPUT_LENGTH:{vector_id}")
        for field in ("convolution", "rhs", "xHat"):
            a, b = vector(left[field]), vector(right[field])
            if len(a) != len(b):
                raise RuntimeError(f"BLOCKED_STAGE07_VECTOR_LENGTH:{vector_id}:{field}")
            for index, (cpp_value, matlab_value) in enumerate(zip(a, b)):
                difference = abs(cpp_value - matlab_value)
                max_continuous = max(max_continuous, difference)
                rows.append(
                    {
                        "vectorId": vector_id,
                        "quantity": field,
                        "sampleIndex": index,
                        "cppValue": f"{cpp_value:.17g}",
                        "matlabValue": f"{matlab_value:.17g}",
                        "absDiff": f"{difference:.17g}",
                    }
                )
        if left["hardDecision"] != right["hardDecision"]:
            hard_mismatches += sum(
                a != b for a, b in zip(left["hardDecision"], right["hardDecision"])
            )
        residual_difference = abs(
            float(left["solverResidual"]) - float(right["solverResidual"])
        )
        max_continuous = max(max_continuous, residual_difference)
        rows.append(
            {
                "vectorId": vector_id,
                "quantity": "solverResidual",
                "sampleIndex": 0,
                "cppValue": left["solverResidual"],
                "matlabValue": right["solverResidual"],
                "absDiff": f"{residual_difference:.17g}",
            }
        )
    if not math.isfinite(max_continuous) or max_continuous > 1e-10:
        raise RuntimeError(f"BLOCKED_STAGE07_CONTINUOUS_DIFF:{max_continuous}")
    if hard_mismatches:
        raise RuntimeError(f"BLOCKED_STAGE07_HARD_MISMATCH:{hard_mismatches}")
    target = results / "stage07_multipath_validation_cpp_matlab_compare.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        "PASS_STAGE07_CPP_MATLAB_COMPARE "
        f"rows={len(rows)} maxAbsDiff={max_continuous:.17g} hardMismatch=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
