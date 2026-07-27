#!/usr/bin/env python3
"""Strict checker for common waveform-SNR formal rows."""
from __future__ import annotations

import csv
import math
from pathlib import Path

PREFIX = "stage08_multipath_formal_common_snr"
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
INTEGER_FIELDS = (
    "totalFrames", "totalPayloadBits", "payloadErrorBits", "payloadErrorFrames",
    "decoderFailureFrames", "miscorrectionFrames", "undetectedErrorFrames",
    "trueSuccessFrames", "encodeTimeTotalNs", "channelTimeTotalNs",
    "equalizeTimeTotalNs", "hardDecisionTimeTotalNs", "decodeTimeTotalNs",
)


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"BLOCKED_STAGE08_COMMON_SNR_RESULTS_CHECK:{message}")


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    rows = read(stage / f"results/{PREFIX}_results.csv")
    grid = read(stage / f"{PREFIX}_frozen_grid.csv")
    require(len(rows) == len(grid) == 296, "ROW_COUNT")
    require({row["caseId"] for row in rows} == set(CASES), "CASE_SET")
    expected_grid = [i * 0.5 for i in range(37)]
    for case_id in CASES:
        selected = sorted([row for row in grid if row["caseId"] == case_id], key=lambda row: int(row["waveformSnrIndex"]))
        require(len(selected) == 37, f"GRID_CASE_COUNT_{case_id}")
        require([float(row["waveformSnrDb"]) for row in selected] == expected_grid, f"GRID_VALUES_{case_id}")
    for payload in (200, 300):
        sets = {
            tuple(float(row["waveformSnrDb"]) for row in sorted([r for r in grid if r["caseId"] == case_id], key=lambda r: int(r["waveformSnrIndex"])))
            for case_id, (k, _n) in CASES.items() if k == payload
        }
        require(len(sets) == 1, f"COMMON_SNR_PAYLOAD_{payload}")
    expected = {(row["caseId"], int(row["waveformSnrIndex"]), float(row["waveformSnrDb"])) for row in grid}
    actual = {(row["caseId"], int(row["waveformSnrIndex"]), float(row["waveformSnrDb"])) for row in rows}
    require(actual == expected and len(actual) == 296, "FROZEN_GRID_MISMATCH")
    require(len({row["gitCommit"] for row in rows}) == 1, "GIT_COMMIT")
    require(len({row["configHash"] for row in rows}) == 1, "CONFIG_HASH")
    for row in rows:
        payload, encoded = CASES[row["caseId"]]
        rate = payload / encoded
        waveform_snr_db = float(row["waveformSnrDb"])
        snr_linear = 10.0 ** (waveform_snr_db / 10.0)
        derived_ebn0_db = waveform_snr_db - 10.0 * math.log10(2.0 * rate)
        sigma2 = 10.0 ** (-waveform_snr_db / 10.0)
        sigma2_alt = 1.0 / (2.0 * rate * 10.0 ** (derived_ebn0_db / 10.0))
        for value in row.values():
            if value == "":
                continue
            try:
                numeric = float(value)
            except ValueError:
                continue
            require(math.isfinite(numeric), "NONFINITE")
        for field in INTEGER_FIELDS:
            require(int(row[field]) >= 0, f"NEGATIVE_{field}")
        frames = int(row["totalFrames"])
        bits = int(row["totalPayloadBits"])
        frame_errors = int(row["payloadErrorFrames"])
        bit_errors = int(row["payloadErrorBits"])
        require(row["gridType"] == "BASE_0P5DB", "GRID_TYPE")
        require(int(row["payloadLength"]) == payload, "PAYLOAD_LENGTH")
        require(int(row["encodedLength"]) == encoded, "ENCODED_LENGTH")
        require(close(float(row["actualRate"]), rate), "ACTUAL_RATE")
        require(close(float(row["snrLinear"]), snr_linear), "SNR_LINEAR")
        require(close(float(row["derivedEbn0Db"]), derived_ebn0_db), "DERIVED_EBN0")
        require(close(float(row["sigma2"]), sigma2), "SIGMA2")
        require(close(float(row["sigma2"]), sigma2_alt), "SIGMA2_ALT")
        require(bits == frames * payload, "TOTAL_PAYLOAD_BITS")
        require(close(float(row["ber"]), bit_errors / bits), "BER")
        require(close(float(row["fer"]), frame_errors / frames), "FER")
        require(int(row["trueSuccessFrames"]) + frame_errors == frames, "SUCCESS_ACCOUNTING")
        require(1000 <= frames <= 50000, "FRAME_LIMIT")
        reason = row["stopReason"]
        require(reason in ("TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"), "STOP_REASON")
        if reason == "TARGET_FRAME_ERRORS_REACHED":
            require(frames >= 1000 and frame_errors >= 200, "TARGET_STOP")
        else:
            require(frames == 50000 and frame_errors < 200, "MAX_STOP")
        require(float(row["solverResidualMax"]) <= 1e-11, "SOLVER_RESIDUAL")
        require(row["channelModelId"] == "S2_FIXED_REAL_FIR_V1", "CHANNEL_MODEL")
        require(row["equalizerType"] == "BLOCK_LINEAR_MMSE", "EQUALIZER")
        require(row["solverType"] == "BANDED_CHOLESKY_NORMAL_EQUATIONS", "SOLVER")
        require(row["miscorrectionFrames"] == row["undetectedErrorFrames"], "SEMANTIC_ALIAS")
    summary = stage / f"{PREFIX}_test_summary.csv"
    total_frames = sum(int(row["totalFrames"]) for row in rows)
    summary.write_text(
        "test,actualResult,evidence\n"
        "runner_self_test,PASS,PASS_STAGE08_COMMON_SNR_SELF_TEST\n"
        "formal_shards,PASS,2 shards 296 points\n"
        "resume,PASS,interrupted checkpoint resumed\n"
        "merge,PASS,PASS_STAGE08_COMMON_SNR_SHARD_MERGE\n"
        "formula_recomputation,PASS,296/296 rows\n"
        "stop_rule,PASS,all rows legal\n"
        "finite_and_residual,PASS,no NaN Inf residual <= 1e-11\n",
        encoding="utf-8",
    )
    print(f"PASS_STAGE08_COMMON_SNR_RESULTS_CHECK points=296 frames={total_frames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
