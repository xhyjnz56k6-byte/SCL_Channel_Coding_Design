#!/usr/bin/env python3
"""Build the corrected S2-08 comparison from scientifically compatible inputs."""

from __future__ import annotations

import csv
import math
from pathlib import Path


TARGETS = (0.1, 0.01, 0.001)
CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"]


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalized(
    row: dict[str, str],
    channel: str,
    profile: str,
    eb_field: str,
    hard_ber_field: str = "channelHardBER",
) -> dict[str, object]:
    rate = float(row["frameRate"])
    source = float(row[eb_field])
    snr = source + 10.0 * math.log10(rate)
    if row.get("snrDb") and abs(float(row["snrDb"]) - snr) > 5e-10:
        raise SystemExit("BLOCKED_BCH_S2_SNR_SEMANTIC_MISMATCH")
    median_receiver = row.get("medianReceiverTimeUs", "")
    p95_receiver = row.get("p95ReceiverTimeUs", "")
    p99_receiver = row.get("p99ReceiverTimeUs", "")
    timing_semantics = "MEASURED_END_TO_END_RECEIVER"
    if not median_receiver:
        if channel == "AWGN":
            median_receiver = row.get("p50DecodeTimeUs", "")
            p95_receiver = row.get("p95DecodeTimeUs", "")
            p99_receiver = row.get("p99DecodeTimeUs", "")
            timing_semantics = "AWGN_DECODE_DOMINATED_LEGACY_BASELINE"
        else:
            timing_semantics = "LEGACY_AVERAGE_ONLY_QUANTILES_UNAVAILABLE"
    return {
        "channelType": channel,
        "profileId": profile,
        "caseName": row["caseName"],
        "payloadGroup": row["payloadLength"],
        "payloadLength": row["payloadLength"],
        "encodedLength": row["encodedLength"],
        "frameRate": row["frameRate"],
        "sourcePayloadEbN0Db": source,
        "snrDb": snr,
        "processedFrames": row["processedFrames"],
        "decodedBitErrors": row["decodedBitErrors"],
        "decodedFrameErrors": row["decodedFrameErrors"],
        "BER": row["BER"],
        "FER": row["FER"],
        "trueSuccessRate": row["trueSuccessRate"],
        "miscorrectionRate": row["miscorrectionRate"],
        "decoderFailureRate": row["decoderFailureRate"],
        "channelHardBER": row.get(hard_ber_field, ""),
        "avgDecodeTimeUs": row.get("avgDecodeTimeUs", ""),
        "avgPreprocessingTimeUs": row.get(
            "avgPreprocessingTimeUs", row.get("avgEqualizationTimeUs", "")
        ),
        "medianPreprocessingTimeUs": row.get(
            "medianPreprocessingTimeUs", row.get("p50EqualizationTimeUs", "")
        ),
        "p95PreprocessingTimeUs": row.get(
            "p95PreprocessingTimeUs", row.get("p95EqualizationTimeUs", "")
        ),
        "p99PreprocessingTimeUs": row.get(
            "p99PreprocessingTimeUs", row.get("p99EqualizationTimeUs", "")
        ),
        "avgTotalReceiverTimeUs": row.get(
            "avgTotalReceiverTimeUs", row.get("avgDecodeTimeUs", "")
        ),
        "medianReceiverTimeUs": median_receiver,
        "p95ReceiverTimeUs": p95_receiver,
        "p99ReceiverTimeUs": p99_receiver,
        "timingSemantics": timing_semantics,
        "xSemantic": "NORMALIZED_WAVEFORM_SNR_PS_OVER_PN",
        "bandwidthConvention": "Bn_EQUALS_Rs",
    }


def interpolate(
    rows: list[dict[str, object]], target: float,
) -> tuple[str, str, str, str]:
    valid = sorted(
        [row for row in rows
         if math.isfinite(float(row["snrDb"]))
         and math.isfinite(float(row["FER"]))
         and float(row["FER"]) > 0.0],
        key=lambda row: float(row["snrDb"]),
    )
    exact = [row for row in valid if abs(float(row["FER"]) - target) <= 1e-15]
    if exact:
        value = str(exact[0]["snrDb"])
        return value, "EXACT_OBSERVED_POINT", value, value
    for left, right in zip(valid, valid[1:]):
        f1, f2 = float(left["FER"]), float(right["FER"])
        if (f1 - target) * (f2 - target) < 0.0 and f1 != f2:
            x1, x2 = float(left["snrDb"]), float(right["snrDb"])
            weight = (math.log10(target) - math.log10(f1)) / (
                math.log10(f2) - math.log10(f1)
            )
            value = x1 + weight * (x2 - x1)
            return (
                f"{value:.17g}", "BRACKETED_LOG_FER_INTERPOLATION",
                f"{x1:.17g}", f"{x2:.17g}",
            )
    return "", "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION", "", ""


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    corrected = stages / "s2_08_channel_adaptation_comparison_corrected"
    published = (
        repo / "Task/BCH/simulation/results/s2_batch2_corrected/published/s2_08"
    )
    cfo_stage = stages / "s2_05_residual_cfo_corrected"
    rows: list[dict[str, object]] = []

    awgn_index = read(
        stages / "s2_03_awgn_baseline_reuse/awgn_baseline_sources.csv"
    )
    for index in awgn_index:
        for row in read(repo / index["sourcePath"]):
            if row["caseName"] == index["caseName"]:
                rows.append(normalized(row, "AWGN", "AWGN", "ebn0Db"))
    for row in read(stages / "s2_04_fixed_multipath_mmse/formal_summary.csv"):
        rows.append(normalized(
            row, "MULTIPATH_MMSE", "MULTIPATH_MMSE",
            "sourcePayloadEbN0Db", "postEqualizationHardBER",
        ))
    for row in read(cfo_stage / "cfo_phi0_zero_snr_summary.csv"):
        rotation = int(float(row["frameRotationDeg"]))
        rows.append(normalized(
            row,
            f"CFO_{rotation}_NO_COMPENSATION_PHI0_ZERO",
            f"CFO_{rotation}_PHI0_ZERO",
            "sourcePayloadEbN0Db",
        ))
    for row in read(
        stages / "s2_06_short_blockage/blockage_formal_snr_summary.csv"
    ):
        profile = "BLOCKAGE_M" if int(row["blockageLength"]) == 16 else "BLOCKAGE_H"
        rows.append(normalized(row, profile, profile, "sourcePayloadEbN0Db"))

    awgn_timing = {
        row["caseName"]: row
        for row in read(corrected / "awgn_receiver_timing_audit.csv")
    }
    impairment_timing_rows = read(
        corrected / "impairment_receiver_timing_audit.csv"
    )
    blockage_timing = {
        (row["caseName"],
         "BLOCKAGE_M" if int(row["blockageLength"]) == 16 else "BLOCKAGE_H"): row
        for row in impairment_timing_rows
        if row["channelType"] == "SHORT_BLOCKAGE"
    }
    cfo_timing = {
        (row["caseName"], int(float(row["frameRotationDeg"]))): row
        for row in impairment_timing_rows
        if row["channelType"] == "RESIDUAL_CFO"
    }
    for row in rows:
        source: dict[str, str] | None = None
        if row["channelType"] == "AWGN":
            source = awgn_timing[str(row["caseName"])]
            row["avgDecodeTimeUs"] = source["avgDecodeTimeUs"]
            row["avgTotalReceiverTimeUs"] = source["avgDecodeTimeUs"]
            row["medianReceiverTimeUs"] = source["p50DecodeTimeUs"]
            row["p95ReceiverTimeUs"] = source["p95DecodeTimeUs"]
            row["p99ReceiverTimeUs"] = source["p99DecodeTimeUs"]
            row["timingSemantics"] = "TIMING_ONLY_RERUN_PROFILE_PREINITIALIZED"
            row["avgPreprocessingTimeUs"] = 0.0
            row["medianPreprocessingTimeUs"] = 0.0
            row["p95PreprocessingTimeUs"] = 0.0
            row["p99PreprocessingTimeUs"] = 0.0
        elif row["channelType"] in {"BLOCKAGE_M", "BLOCKAGE_H"}:
            source = blockage_timing[
                (str(row["caseName"]), str(row["channelType"]))
            ]
            for field in (
                "avgDecodeTimeUs", "avgTotalReceiverTimeUs",
                "medianReceiverTimeUs", "p95ReceiverTimeUs",
                "p99ReceiverTimeUs", "avgPreprocessingTimeUs",
                "medianPreprocessingTimeUs", "p95PreprocessingTimeUs",
                "p99PreprocessingTimeUs",
            ):
                row[field] = source[field]
            row["timingSemantics"] = "TIMING_ONLY_RERUN_PROFILE_PREINITIALIZED"
        elif str(row["channelType"]).startswith("CFO_"):
            rotation = int(str(row["channelType"]).split("_")[1])
            source = cfo_timing[(str(row["caseName"]), rotation)]
            for field in (
                "avgDecodeTimeUs", "avgTotalReceiverTimeUs",
                "medianReceiverTimeUs", "p95ReceiverTimeUs",
                "p99ReceiverTimeUs", "avgPreprocessingTimeUs",
                "medianPreprocessingTimeUs", "p95PreprocessingTimeUs",
                "p99PreprocessingTimeUs",
            ):
                row[field] = source[field]
            row["timingSemantics"] = "TIMING_ONLY_RERUN_PROFILE_PREINITIALIZED"

    for destination in (corrected, published):
        write(destination / "channel_adaptation_summary.csv", rows)

    audits: list[dict[str, object]] = []
    losses: list[dict[str, object]] = []
    channels = sorted({str(row["channelType"]) for row in rows})
    for case in CASES:
        awgn = [
            row for row in rows
            if row["caseName"] == case and row["channelType"] == "AWGN"
        ]
        for target in TARGETS:
            awgn_value, awgn_status, awgn_left, awgn_right = interpolate(
                awgn, target
            )
            audits.append({
                "caseName": case,
                "channelType": "AWGN",
                "profileId": "AWGN",
                "targetFER": target,
                "interpolatedSnrDb": awgn_value,
                "status": awgn_status,
                "leftSnrDb": awgn_left,
                "rightSnrDb": awgn_right,
                "method": "LOG_FER_LINEAR_SNR_WITHIN_OBSERVED_BRACKET",
            })
            for channel in channels:
                if channel == "AWGN":
                    continue
                selected = [
                    row for row in rows
                    if row["caseName"] == case and row["channelType"] == channel
                ]
                value, status, left, right = interpolate(selected, target)
                audits.append({
                    "caseName": case,
                    "channelType": channel,
                    "profileId": selected[0]["profileId"] if selected else "",
                    "targetFER": target,
                    "interpolatedSnrDb": value,
                    "status": status,
                    "leftSnrDb": left,
                    "rightSnrDb": right,
                    "method": "LOG_FER_LINEAR_SNR_WITHIN_OBSERVED_BRACKET",
                })
                valid_statuses = {
                    "EXACT_OBSERVED_POINT",
                    "BRACKETED_LOG_FER_INTERPOLATION",
                }
                loss = (
                    float(value) - float(awgn_value)
                    if status in valid_statuses and awgn_status in valid_statuses
                    else ""
                )
                losses.append({
                    "caseName": case,
                    "channelType": channel,
                    "profileId": selected[0]["profileId"] if selected else "",
                    "targetFER": target,
                    "channelSnrDb": value,
                    "awgnSnrDb": awgn_value,
                    "snrLossDb": loss,
                    "status": (
                        "VALID_WITHIN_OBSERVED_BRACKETS" if loss != ""
                        else status
                    ),
                })
    for destination in (corrected, published):
        write(destination / "comparison_interpolation_audit.csv", audits)
        write(destination / "target_fer_snr_loss_summary.csv", losses)

    risk = [{
        "channelType": row["channelType"],
        "profileId": row["profileId"],
        "caseName": row["caseName"],
        "snrDb": row["snrDb"],
        "trueSuccessRate": row["trueSuccessRate"],
        "miscorrectionRate": row["miscorrectionRate"],
        "decoderFailureRate": row["decoderFailureRate"],
        "interpretation": (
            "SYNDROME_LOOKUP_FAILURE_ZERO_DOES_NOT_IMPLY_TRUE_SUCCESS"
            if row["caseName"] in {"BCH-S200", "BCH-S300"}
            else "EXPLICIT_BM_CHIEN_FAILURE_AVAILABLE"
        ),
    } for row in rows]
    timing = [{
        "channelType": row["channelType"],
        "profileId": row["profileId"],
        "caseName": row["caseName"],
        "snrDb": row["snrDb"],
        "avgDecodeTimeUs": row["avgDecodeTimeUs"],
        "avgTotalReceiverTimeUs": row["avgTotalReceiverTimeUs"],
        "avgPreprocessingTimeUs": row["avgPreprocessingTimeUs"],
        "medianPreprocessingTimeUs": row["medianPreprocessingTimeUs"],
        "p95PreprocessingTimeUs": row["p95PreprocessingTimeUs"],
        "p99PreprocessingTimeUs": row["p99PreprocessingTimeUs"],
        "medianReceiverTimeUs": row["medianReceiverTimeUs"],
        "p95ReceiverTimeUs": row["p95ReceiverTimeUs"],
        "p99ReceiverTimeUs": row["p99ReceiverTimeUs"],
        "timingSemantics": row["timingSemantics"],
    } for row in rows]
    for destination in (corrected, published):
        write(destination / "miscorrection_risk_summary.csv", risk)
        write(destination / "decoder_failure_risk_summary.csv", risk)
        write(destination / "receiver_timing_summary.csv", timing)
    print("PASS_BCH_S2_CORRECTED_CHANNEL_COMPARISON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
