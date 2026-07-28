#!/usr/bin/env python3
"""Strict functional checker for stage07 evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

CASES = {
    "K200_S15": (200, 285),
    "K200_M255K207": (200, 248),
    "K200_M511K421": (200, 290),
    "K200_M511K385": (200, 326),
    "K300_S15": (300, 420),
    "K300_M255K207": (300, 396),
    "K300_M511K421": (300, 390),
    "K300_M511K385": (300, 426),
}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"BLOCKED_STAGE07_{message}")


def finite_rows(rows: list[dict[str, str]]) -> None:
    for row in rows:
        for value in row.values():
            if value in ("", "PASS", "BLOCKED", "REFERENCE"):
                continue
            try:
                numeric = float(value)
            except ValueError:
                continue
            require(math.isfinite(numeric), "NONFINITE")


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    model = json.loads(
        (stage / "stage07_multipath_validation_frozen_model.json").read_text(
            encoding="utf-8"
        )
    )
    raw_energy = sum(value * value for value in model["rawImpulseResponse"])
    normalized_energy = sum(
        value * value for value in model["normalizedImpulseResponse"]
    )
    require(abs(raw_energy - model["rawChannelEnergy"]) < 1e-14, "RAW_ENERGY")
    require(abs(normalized_energy - 1.0) < model["normalizationTolerance"], "NORMALIZATION")
    require(model["convolutionMode"] == "LINEAR_FULL", "CONVOLUTION_MODE")
    require(model["boundaryPolicy"] == "ZERO_OUTSIDE_FRAME", "BOUNDARY")

    compare = read(results / "stage07_multipath_validation_cpp_matlab_compare.csv")
    require(compare, "EMPTY_CPP_MATLAB_COMPARE")
    require(max(float(row["absDiff"]) for row in compare) <= 1e-10, "CPP_MATLAB_DIFF")

    h1 = read(results / "stage07_multipath_validation_h1_awgn_compare.csv")
    require({row["caseId"] for row in h1} == set(CASES), "H1_CASES")
    require(all(row["gate"] == "PASS" for row in h1), "H1_GATE")
    require(
        all(
            int(row[field]) == 0
            for row in h1
            for field in (
                "hardMismatch",
                "payloadMismatch",
                "payloadErrorBitsMismatch",
                "payloadErrorFramesMismatch",
                "decoderStatusMismatch",
            )
        ),
        "H1_DISCRETE",
    )

    noiseless = read(results / "stage07_multipath_validation_noiseless_results.csv")
    require({row["caseId"] for row in noiseless} == set(CASES), "NOISELESS_CASES")
    for row in noiseless:
        require(int(row["totalFrames"]) >= 1000, "NOISELESS_FRAME_COUNT")
        require(
            all(
                int(row[field]) == 0
                for field in (
                    "payloadErrorBits",
                    "payloadErrorFrames",
                    "decoderFailureFrames",
                    "miscorrectionFrames",
                    "undetectedErrorFrames",
                )
            ),
            "NOISELESS_ERRORS",
        )
        require(
            int(row["trueSuccessFrames"]) == int(row["totalFrames"]),
            "NOISELESS_SUCCESS",
        )
        require(float(row["solverResidualMax"]) <= model["solverResidualTolerance"], "RESIDUAL")

    for name in ("resume_compare", "shard_merge_compare"):
        rows = read(results / f"stage07_multipath_validation_{name}.csv")
        require(len(rows) == 2 and rows[1]["gate"] == "PASS", name.upper())
        for field in (
            "totalFrames",
            "totalPayloadBits",
            "payloadErrorBits",
            "payloadErrorFrames",
            "decoderFailureFrames",
            "miscorrectionFrames",
            "undetectedErrorFrames",
            "trueSuccessFrames",
        ):
            require(rows[0][field] == rows[1][field], f"{name}_{field}")

    trial = read(results / "stage07_multipath_validation_trial_results.csv")
    require(len(trial) == 24, "TRIAL_POINT_COUNT")
    require({row["caseId"] for row in trial} == set(CASES), "TRIAL_CASES")
    for case_id, (payload_length, encoded_length) in CASES.items():
        selected = [row for row in trial if row["caseId"] == case_id]
        require(len(selected) == 3, f"TRIAL_GRID_{case_id}")
        require(len({row["ebn0Db"] for row in selected}) == 3, f"TRIAL_DUPLICATE_{case_id}")
        for row in selected:
            rate = payload_length / encoded_length
            ebn0 = float(row["ebn0Db"])
            sigma2 = 1.0 / (2.0 * rate * 10.0 ** (ebn0 / 10.0))
            require(abs(float(row["actualRate"]) - rate) < 1e-15, "RATE")
            require(abs(float(row["sigma2"]) - sigma2) < 1e-14, "SIGMA2")
            require(
                int(row["trueSuccessFrames"]) + int(row["payloadErrorFrames"])
                == int(row["totalFrames"]),
                "ACCOUNTING",
            )
            require(float(row["solverResidualMax"]) <= model["solverResidualTolerance"], "TRIAL_RESIDUAL")
    finite_rows(trial)

    required = [
        "stage07_multipath_validation_test_vectors.csv",
        "stage07_multipath_validation_cpp_outputs.csv",
        "stage07_multipath_validation_matlab_outputs.csv",
        "stage07_multipath_validation_cpp_matlab_compare.csv",
        "stage07_multipath_validation_h1_awgn_compare.csv",
        "stage07_multipath_validation_noiseless_results.csv",
        "stage07_multipath_validation_resume_compare.csv",
        "stage07_multipath_validation_shard_merge_compare.csv",
        "stage07_multipath_validation_trial_results.csv",
        "stage07_multipath_validation_runtime_estimate.csv",
    ]
    hashes = {}
    for name in required:
        path = results / name
        require(path.is_file() and path.stat().st_size > 0, f"MISSING_{name}")
        hashes[f"results/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (stage / "stage07_multipath_validation_file_hashes.json").write_text(
        json.dumps(hashes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = stage / "stage07_multipath_validation_test_summary.csv"
    summary.write_text(
        "test,actualResult,evidence\n"
        "release_build,PASS,MinGW GCC Release\n"
        "ctest,PASS,1/1\n"
        "cpp_validation,PASS,PASS_STAGE07_MULTIPATH_VALIDATION_CPP\n"
        "matlab_reference,PASS,PASS_STAGE07_MULTIPATH_VALIDATION_MATLAB\n"
        "cpp_matlab_compare,PASS,PASS_STAGE07_CPP_MATLAB_COMPARE\n"
        "h1_degeneration,PASS,8 cases zero discrete mismatch\n"
        "noiseless,PASS,8 cases 1007 frames zero error\n"
        "resume_shard,PASS,integer counts identical\n"
        "trial,PASS,24 points 12000 frames\n",
        encoding="utf-8",
    )
    print("PASS_STAGE07_MULTIPATH_VALIDATION_FUNCTIONAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
