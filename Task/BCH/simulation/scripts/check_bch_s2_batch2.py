#!/usr/bin/env python3
"""Strict business checker for BCH S2-05..S2-09 and batch plots."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_result_rows(path: Path, expected: int) -> tuple[int, int]:
    rows = read(path)
    if len(rows) != expected:
        raise SystemExit(f"BLOCKED_BCH_S2_ROW_COUNT: {path} {len(rows)} != {expected}")
    frames = 0
    for row in rows:
        count = int(row["processedFrames"])
        frames += count
        if int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != count:
            raise SystemExit("BLOCKED_BCH_S2_TRUE_SUCCESS_ACCOUNTING")
        if int(row["reportedSuccessFrames"]) + int(row["decoderFailureFrames"]) != count:
            raise SystemExit("BLOCKED_BCH_S2_REPORTED_SUCCESS_ACCOUNTING")
        if int(row["processedPayloadBits"]) == 0:
            raise SystemExit("BLOCKED_BCH_S2_ZERO_PAYLOAD_BITS")
        expected_ber = int(row["decodedBitErrors"]) / int(row["processedPayloadBits"])
        if abs(expected_ber - float(row["BER"])) > 1e-15:
            raise SystemExit("BLOCKED_BCH_S2_BER_ACCOUNTING")
        expected_fer = int(row["decodedFrameErrors"]) / count
        if abs(expected_fer - float(row["FER"])) > 1e-15:
            raise SystemExit("BLOCKED_BCH_S2_FER_ACCOUNTING")
        snr = float(row["sourcePayloadEbN0Db"]) + 10.0 * math.log10(
            float(row["frameRate"]))
        if abs(snr - float(row["snrDb"])) > 5e-10:
            raise SystemExit("BLOCKED_BCH_S2_SNR_SEMANTIC_MISMATCH")
        for field in ("BER", "FER", "trueSuccessRate", "miscorrectionRate",
                      "decoderFailureRate", "avgDecodeTimeUs",
                      "avgTotalReceiverTimeUs"):
            if not math.isfinite(float(row[field])):
                raise SystemExit("BLOCKED_BCH_S2_NONFINITE_RESULT")
        if row["noisePolicyVersion"] != "2":
            raise SystemExit("BLOCKED_BCH_S2_NOISE_POLICY")
    return len(rows), frames


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    cfo_stage = stages / "s2_05_residual_cfo"
    blockage_stage = stages / "s2_06_short_blockage"
    burst_stage = stages / "s2_07_burst_sensitivity"
    smoke_cfo = check_result_rows(cfo_stage / "smoke_summary.csv", 420)
    phase = check_result_rows(cfo_stage / "cfo_formal_phase_summary.csv", 720)
    cfo_snr_rows = read(cfo_stage / "cfo_formal_snr_summary.csv")
    check_result_rows(cfo_stage / "cfo_formal_snr_summary.csv", len(cfo_snr_rows))
    smoke_blockage = check_result_rows(blockage_stage / "smoke_summary.csv", 1680)
    blockage_formal = check_result_rows(
        blockage_stage / "blockage_formal_parameter_summary.csv", 6300)
    blockage_snr_rows = read(blockage_stage / "blockage_formal_snr_summary.csv")
    check_result_rows(blockage_stage / "blockage_formal_snr_summary.csv",
                      len(blockage_snr_rows))
    smoke_burst = check_result_rows(burst_stage / "smoke_summary.csv", 540)
    pure = check_result_rows(burst_stage / "pure_burst_summary.csv", 630)
    awgn_burst = check_result_rows(burst_stage / "awgn_burst_summary.csv", 1260)

    baseline = read(stages / "s2_08_channel_adaptation_comparison/baseline_sources.csv")
    if len(baseline) != 10 or any(row["reuseStatus"] not in {
        "REUSED_S1_FORMAL_AWGN_BASELINE",
        "REUSED_S2_04_FIXED_MULTIPATH_MMSE",
    } for row in baseline):
        raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")
    for row in baseline:
        source = repo / row["sourcePath"]
        if sha256(source) != row["sourceSha256"]:
            raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")

    interpolation = read(
        stages / "s2_08_channel_adaptation_comparison/comparison_interpolation_audit.csv")
    allowed = {"VALID", "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION",
               "UNDEFINED_ZERO_DENOMINATOR", "INSUFFICIENT_VALID_POINTS"}
    if not interpolation or any(row["status"] not in allowed for row in interpolation):
        raise SystemExit("BLOCKED_BCH_S2_INTERPOLATION_AUDIT")

    matlab = read(stages / "s2_09_matlab_channel_reference/matlab_reference_summary.csv")
    mismatch_fields = [
        "hardBitMismatches", "decodedPayloadBitMismatches",
        "frameErrorMismatches", "reportedStatusMismatches",
        "miscorrectionMismatches", "decoderFailureMismatches",
    ]
    if (len(matlab) != 45 or sum(int(row["comparedFrames"]) for row in matlab) != 4500
            or any(float(row["maxSampleAbsDiff"]) > 1e-12 for row in matlab)
            or any(int(row[field]) != 0 for row in matlab for field in mismatch_fields)
            or any(row["gate"] != "PASS" for row in matlab)):
        raise SystemExit("BLOCKED_BCH_S2_09_MATLAB_MISMATCH")

    batch = stages / "s2_multi_channel_adaptation"
    resume = read(batch / "resume_shard_audit.csv")
    if not resume or any(row["status"] != "PASS" for row in resume):
        raise SystemExit("BLOCKED_BCH_S2_BATCH2_RESUME_SHARD")
    manifest = json.loads((batch / "plot_manifest.json").read_text(encoding="utf-8"))
    if manifest["nonPngCount"] != 0 or manifest["figureCount"] != 12:
        raise SystemExit("BLOCKED_BCH_S2_BATCH2_PLOT_COUNT")
    for figure in manifest["figures"]:
        png = batch / "figures" / figure["filename"]
        source = repo / figure["sourceCsv"]
        data = repo / figure["figureDataCsv"]
        if (png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or
                sha256(png) != figure["pngSha256"] or
                sha256(source) != figure["sourceCsvSha256"] or
                sha256(data) != figure["figureDataSha256"] or
                figure["figureDataPointCount"] != len(read(data)) or
                len(figure["visualStyleKeys"]) !=
                len(set(figure["visualStyleKeys"]))):
            raise SystemExit("BLOCKED_BCH_S2_BATCH2_PLOT_AUDIT")
        if figure["xColumn"] == "snrDb":
            for row in read(data):
                expected = float(row["sourcePayloadEbN0Db"]) + 10.0 * math.log10(
                    float(row["frameRate"]))
                if abs(expected - float(row["snrDb"])) > 5e-10:
                    raise SystemExit("BLOCKED_BCH_S2_BATCH2_FIGURE_SNR")
    print(f"PASS_BCH_S2_05_RESIDUAL_CFO smokePoints={smoke_cfo[0]} "
          f"formalPhasePoints={phase[0]} formalSnrPoints={len(cfo_snr_rows)}")
    print(f"PASS_BCH_S2_06_SHORT_BLOCKAGE smokePoints={smoke_blockage[0]} "
          f"formalPoints={blockage_formal[0]} formalSnrPoints={len(blockage_snr_rows)}")
    print(f"PASS_BCH_S2_07_BURST_SENSITIVITY smokePoints={smoke_burst[0]} "
          f"purePoints={pure[0]} awgnBurstPoints={awgn_burst[0]}")
    print("PASS_BCH_S2_08_CHANNEL_ADAPTATION_COMPARISON")
    print("PASS_BCH_S2_09_MATLAB_CHANNEL_REFERENCE frames=4500")
    print("PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
