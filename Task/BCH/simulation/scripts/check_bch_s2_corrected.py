#!/usr/bin/env python3
"""Strict gate checker for the BCH S2 scientific-semantics correction."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path


ALLOWED_TOLERANCE = {
    "EXACT_OBSERVED_POINT",
    "BRACKETED_INTERVAL",
    "LOWER_BOUND_AT_TEST_LIMIT",
    "BELOW_MINIMUM_TESTED_PARAMETER",
    "NON_MONOTONIC_NO_UNIQUE_THRESHOLD",
    "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION",
}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, gate: str) -> None:
    if not condition:
        raise SystemExit(gate)


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=repo, text=True
    ).strip()
    require(
        branch == "bch-s2-batch2-cfo-blockage-burst-final-audit",
        "BLOCKED_BCH_S2_CORRECTED_WRONG_BRANCH",
    )
    stages = repo / "Task/BCH/simulation/stages"
    cfo_stage = stages / "s2_05_residual_cfo_corrected"
    comparison = stages / "s2_08_channel_adaptation_comparison_corrected"
    result_root = repo / "Task/BCH/simulation/results/s2_batch2_corrected"
    require(result_root.is_dir(), "BLOCKED_BCH_S2_CORRECTED_RESULTS_NOT_UNDER_RESULTS")

    main_rows = read(cfo_stage / "cfo_phi0_zero_summary.csv")
    snr_rows = read(cfo_stage / "cfo_phi0_zero_snr_summary.csv")
    phase_rows = read(cfo_stage / "initial_phase_sensitivity_summary.csv")
    require(len(main_rows) == 180, "BLOCKED_BCH_S2_CORRECTED_CFO_MAIN_COUNT")
    require(
        all(float(row["initialPhaseDeg"]) == 0.0 for row in main_rows + snr_rows),
        "BLOCKED_BCH_S2_CORRECTED_CFO_PHASE_CONTAMINATION",
    )
    require(
        all(int(row["processedFrames"]) == 5000 for row in main_rows),
        "BLOCKED_BCH_S2_CORRECTED_CFO_MAIN_FRAMES",
    )
    require(
        len(phase_rows) == 40
        and {float(row["initialPhaseDeg"]) for row in phase_rows}
        == {0.0, 45.0, 90.0, 135.0}
        and {float(row["frameRotationDeg"]) for row in phase_rows} == {0.0, 30.0},
        "BLOCKED_BCH_S2_INITIAL_PHASE_SENSITIVITY",
    )
    for row in main_rows + snr_rows + phase_rows:
        require(
            int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"])
            == int(row["processedFrames"]),
            "BLOCKED_BCH_S2_CORRECTED_ACCOUNTING",
        )
        require(
            all(math.isfinite(float(row[field])) for field in (
                "BER", "FER", "medianReceiverTimeUs",
                "p95ReceiverTimeUs", "p99ReceiverTimeUs",
            )),
            "BLOCKED_BCH_S2_CORRECTED_NONFINITE",
        )

    tolerance_rows: list[dict[str, str]] = []
    for name in (
        "cfo_tolerance_summary.csv",
        "blockage_tolerance_summary.csv",
        "burst_tolerance_summary.csv",
    ):
        rows = read(comparison / name)
        require(
            rows and all(row["status"] in ALLOWED_TOLERANCE for row in rows),
            "BLOCKED_BCH_S2_TOLERANCE_STATUS",
        )
        for row in rows:
            if row["status"] == "LOWER_BOUND_AT_TEST_LIMIT":
                require(
                    row["maximumToleratedParameter"] == ""
                    and row["lowerBound"] != ""
                    and row["upperBound"] == "",
                    "BLOCKED_BCH_S2_TOLERANCE_LIMIT_SEMANTICS",
                )
            if row["status"] == "BRACKETED_INTERVAL":
                require(
                    row["maximumToleratedParameter"] == ""
                    and row["lowerBound"] != ""
                    and row["upperBound"] != "",
                    "BLOCKED_BCH_S2_TOLERANCE_BRACKET_SEMANTICS",
                )
        tolerance_rows.extend(rows)

    theory = read(comparison / "burst_theory_gate.csv")
    require(
        len(theory) == 5 and all(row["status"] == "PASS" for row in theory),
        "BLOCKED_BCH_S2_BURST_GUARANTEED_CORRECTION_VIOLATION",
    )
    expected = {
        "BCH-S200": 1, "BCH-S300": 1, "BCH-B200": 6,
        "BCH-B300": 10, "BCH-B300-426": 14,
    }
    require(
        all(
            int(row["guaranteedBurstLengthMax"]) == expected[row["caseName"]]
            and int(row["decodedFrameErrors"]) == 0
            for row in theory
        ),
        "BLOCKED_BCH_S2_BURST_GUARANTEED_CORRECTION_VIOLATION",
    )

    manifest = json.loads(
        (comparison / "plot_manifest.json").read_text(encoding="utf-8")
    )
    require(
        manifest["figureCount"] >= 22
        and manifest["gate"] == "PASS_BCH_S2_CORRECTED_PLOT_AUDIT",
        "BLOCKED_BCH_S2_CORRECTED_PLOT_AUDIT",
    )
    for figure in manifest["figures"]:
        path = comparison / "figures" / figure["filename"]
        require(
            path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
            "BLOCKED_BCH_S2_CORRECTED_NON_PNG",
        )

    matlab = read(
        stages / "s2_09_matlab_channel_reference_corrected/"
        "matlab_reference_summary.csv"
    )
    mismatch_fields = (
        "maxReceivedAbsDiff", "maxPerfectCompensatedAbsDiff",
        "maxPerfectAwgnRealAbsDiff", "noCompHardBitMismatches",
        "perfectHardBitMismatches", "noCompDecodedPayloadBitMismatches",
        "perfectDecodedPayloadBitMismatches", "frameErrorMismatches",
    )
    require(
        len(matlab) == 35
        and sum(int(row["comparedFrames"]) for row in matlab) == 3500
        and all(float(row[field]) <= 1e-12 for row in matlab
                for field in mismatch_fields[:3])
        and all(int(row[field]) == 0 for row in matlab
                for field in mismatch_fields[3:])
        and all(row["gate"] == "PASS" for row in matlab),
        "BLOCKED_BCH_S2_CORRECTED_MATLAB_MISMATCH",
    )

    timing = read(comparison / "impairment_receiver_timing_audit.csv")
    require(
        len(timing) == 20
        and all(float(row["medianReceiverTimeUs"]) > 0.0 for row in timing)
        and all(float(row["p95ReceiverTimeUs"]) >=
                float(row["medianReceiverTimeUs"]) for row in timing),
        "BLOCKED_BCH_S2_CORRECTED_TIMING_AUDIT",
    )
    require(
        all(float(row["medianPreprocessingTimeUs"]) >= 0.0 for row in timing)
        and all(float(row["p95PreprocessingTimeUs"]) >=
                float(row["medianPreprocessingTimeUs"]) for row in timing),
        "BLOCKED_BCH_S2_CORRECTED_PREPROCESSING_TIMING_AUDIT",
    )
    awgn_timing = read(comparison / "awgn_receiver_timing_audit.csv")
    require(
        len(awgn_timing) == 5
        and all(float(row["p50DecodeTimeUs"]) > 0.0 for row in awgn_timing)
        and all(float(row["p95DecodeTimeUs"]) >=
                float(row["p50DecodeTimeUs"]) for row in awgn_timing)
        and float(next(
            row for row in awgn_timing if row["caseName"] == "BCH-B300-426"
        )["avgDecodeTimeUs"]) < 1000.0,
        "BLOCKED_BCH_S2_CORRECTED_AWGN_TIMING_AUDIT",
    )
    status_counts: dict[str, int] = {}
    for row in tolerance_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    print("PASS_BCH_S2_CFO_PHI0_ZERO_CORRECTED")
    print("PASS_BCH_S2_STRICT_TOLERANCE_CLASSIFICATION " + " ".join(
        f"{key}={value}" for key, value in sorted(status_counts.items())
    ))
    print("PASS_BCH_S2_BURST_THEORY_GATE")
    print(f"PASS_BCH_S2_CORRECTED_PLOT_AUDIT figures={manifest['figureCount']}")
    print("PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE frames=3500")
    print("PASS_BCH_S2_CORRECTED_CHANNEL_COMPARISON")
    print("PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION_SCIENTIFIC_GATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
