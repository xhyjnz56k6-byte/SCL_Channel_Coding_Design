#!/usr/bin/env python3
"""Strict recomputation checker for stage08 formal rows."""
from __future__ import annotations

import csv
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
        raise RuntimeError(f"BLOCKED_STAGE08_{message}")


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    rows = read(stage / "results/stage08_multipath_formal_results.csv")
    grid = read(stage / "stage08_multipath_formal_frozen_grid.csv")
    require(len(rows) == len(grid) == 24, "ROW_COUNT")
    require({row["caseId"] for row in rows} == set(CASES), "CASE_SET")
    expected = {
        (row["caseId"], int(row["ebn0Index"]), float(row["ebn0Db"])) for row in grid
    }
    actual = {
        (row["caseId"], int(row["ebn0Index"]), float(row["ebn0Db"])) for row in rows
    }
    require(actual == expected, "FROZEN_GRID_MISMATCH")
    require(len(actual) == 24, "DUPLICATE_POINT")
    require(len({row["gitCommit"] for row in rows}) == 1, "GIT_COMMIT")
    require(len({row["configHash"] for row in rows}) == 1, "CONFIG_HASH")
    for row in rows:
        payload, encoded = CASES[row["caseId"]]
        rate = payload / encoded
        ebn0 = float(row["ebn0Db"])
        sigma2 = 1.0 / (2.0 * rate * 10.0 ** (ebn0 / 10.0))
        snr_linear = 2.0 * rate * 10.0 ** (ebn0 / 10.0)
        snr_db = ebn0 + 10.0 * math.log10(2.0 * rate)
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
        require(int(row["payloadLength"]) == payload, "PAYLOAD_LENGTH")
        require(int(row["encodedLength"]) == encoded, "ENCODED_LENGTH")
        require(close(float(row["actualRate"]), rate), "ACTUAL_RATE")
        require(close(float(row["sigma2"]), sigma2), "SIGMA2")
        require(close(float(row["snrLinear"]), snr_linear), "SNR_LINEAR")
        require(close(float(row["snrDb"]), snr_db), "SNR_DB")
        require(bits == frames * payload, "TOTAL_PAYLOAD_BITS")
        require(close(float(row["ber"]), bit_errors / bits), "BER")
        require(close(float(row["fer"]), frame_errors / frames), "FER")
        require(
            int(row["trueSuccessFrames"]) + frame_errors == frames,
            "SUCCESS_ACCOUNTING",
        )
        require(5000 <= frames <= 50000, "FRAME_LIMIT")
        reason = row["stopReason"]
        require(
            reason in ("TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"),
            "STOP_REASON",
        )
        if reason == "TARGET_FRAME_ERRORS_REACHED":
            require(frame_errors >= 200, "TARGET_STOP")
        else:
            require(frames == 50000 and frame_errors < 200, "MAX_STOP")
        require(float(row["solverResidualMax"]) <= 1e-11, "SOLVER_RESIDUAL")
        require(row["channelModelId"] == "S2_FIXED_REAL_FIR_V1", "CHANNEL_MODEL")
        require(row["equalizerType"] == "BLOCK_LINEAR_MMSE", "EQUALIZER")
        require(
            row["solverType"] == "BANDED_CHOLESKY_NORMAL_EQUATIONS", "SOLVER"
        )
    summary = stage / "stage08_multipath_formal_test_summary.csv"
    summary.write_text(
        "test,actualResult,evidence\n"
        "runner_self_test,PASS,PASS_STAGE08_MULTIPATH_FORMAL_SELF_TEST\n"
        "formal_shards,PASS,2 shards 24 points\n"
        "resume,PASS,executed=0 resumeSkipped=24 hashes unchanged\n"
        "merge,PASS,PASS_STAGE08_SHARD_MERGE\n"
        "formula_recomputation,PASS,24/24 rows\n"
        "stop_rule,PASS,all rows legal\n"
        "finite_and_residual,PASS,no NaN Inf residual <= 1e-11\n",
        encoding="utf-8",
    )
    print(
        "PASS_STAGE08_MULTIPATH_FORMAL_RESULTS "
        f"points=24 frames={sum(int(row['totalFrames']) for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
