#!/usr/bin/env python3
"""Build the auditable S2-08 multi-channel comparison without extrapolation."""

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
        raise RuntimeError(f"empty comparison output: {path}")
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
    row: dict[str, str], channel: str, profile: str,
    eb_field: str, hard_ber_field: str = "channelHardBER",
) -> dict[str, object]:
    rate = float(row["frameRate"])
    source = float(row[eb_field])
    snr = source + 10.0 * math.log10(rate)
    if "snrDb" in row and abs(float(row["snrDb"]) - snr) > 5e-10:
        raise SystemExit("BLOCKED_BCH_S2_SNR_SEMANTIC_MISMATCH")
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
        "avgTotalReceiverTimeUs": row.get("avgTotalReceiverTimeUs",
                                           row.get("avgDecodeTimeUs", "")),
        "xSemantic": "NORMALIZED_WAVEFORM_SNR_PS_OVER_PN",
        "bandwidthConvention": "Bn_EQUALS_Rs",
    }


def interpolate(
    rows: list[dict[str, object]], target: float,
) -> tuple[str, str, str, str]:
    valid = sorted(
        [row for row in rows
         if math.isfinite(float(row["snrDb"])) and
         math.isfinite(float(row["FER"])) and float(row["FER"]) > 0.0],
        key=lambda row: float(row["snrDb"]),
    )
    if len(valid) < 2:
        return "", "INSUFFICIENT_VALID_POINTS", "", ""
    exact = [row for row in valid
             if abs(float(row["FER"]) - target) <= 1e-15]
    if exact:
        return str(exact[0]["snrDb"]), "VALID", str(exact[0]["snrDb"]), str(exact[0]["snrDb"])
    for left, right in zip(valid, valid[1:]):
        f1, f2 = float(left["FER"]), float(right["FER"])
        if (f1 - target) * (f2 - target) < 0.0 and f1 != f2:
            x1, x2 = float(left["snrDb"]), float(right["snrDb"])
            weight = (math.log10(target) - math.log10(f1)) / (
                math.log10(f2) - math.log10(f1))
            value = x1 + weight * (x2 - x1)
            return f"{value:.17g}", "VALID", f"{x1:.17g}", f"{x2:.17g}"
    return "", "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION", "", ""


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    output_dir = stages / "s2_08_channel_adaptation_comparison"
    rows: list[dict[str, object]] = []
    awgn_index = read(stages / "s2_03_awgn_baseline_reuse/awgn_baseline_sources.csv")
    for index in awgn_index:
        for row in read(repo / index["sourcePath"]):
            if row["caseName"] == index["caseName"]:
                rows.append(normalized(row, "AWGN", "AWGN",
                                       "ebn0Db", "channelHardBER"))
    for row in read(stages / "s2_04_fixed_multipath_mmse/formal_summary.csv"):
        rows.append(normalized(row, "MULTIPATH_MMSE", "FIXED_MULTIPATH_MMSE",
                               "sourcePayloadEbN0Db", "postEqualizationHardBER"))
    for row in read(stages / "s2_05_residual_cfo/cfo_snr_aggregate_summary.csv"):
        rows.append(normalized(
            row, f"CFO_{int(float(row['frameRotationDeg']))}_NO_COMPENSATION",
            f"CFO_{int(float(row['frameRotationDeg']))}",
            "sourcePayloadEbN0Db"))
    for row in read(stages / "s2_06_short_blockage/blockage_formal_snr_summary.csv"):
        length = int(row["blockageLength"])
        profile = "BLOCKAGE_M" if length == 16 else "BLOCKAGE_H"
        rows.append(normalized(row, profile, profile, "sourcePayloadEbN0Db"))
    for row in read(stages / "s2_07_burst_sensitivity/awgn_burst_summary.csv"):
        if row["burstStartPolicy"] == "UNIFORM_RANDOM":
            rows.append(normalized(row, "AWGN_BURST",
                                   f"AWGN_BURST_L{row['burstLength']}",
                                   "sourcePayloadEbN0Db"))
    write(output_dir / "channel_adaptation_summary.csv", rows)

    audits: list[dict[str, object]] = []
    losses: list[dict[str, object]] = []
    channels = sorted({str(row["channelType"]) for row in rows})
    for case in CASES:
        awgn = [row for row in rows
                if row["caseName"] == case and row["channelType"] == "AWGN"]
        for target in TARGETS:
            awgn_snr, awgn_status, awgn_left, awgn_right = interpolate(awgn, target)
            audits.append({
                "caseName": case, "channelType": "AWGN", "profileId": "AWGN",
                "targetFER": target, "interpolatedSnrDb": awgn_snr,
                "status": awgn_status, "leftSnrDb": awgn_left,
                "rightSnrDb": awgn_right, "method": "LOG_FER_LINEAR_SNR",
            })
            for channel in channels:
                if channel == "AWGN":
                    continue
                profiles = sorted({
                    str(row["profileId"]) for row in rows
                    if row["caseName"] == case and row["channelType"] == channel
                })
                for profile in profiles:
                    selected = [row for row in rows if row["caseName"] == case
                                and row["channelType"] == channel
                                and row["profileId"] == profile]
                    value, status, left, right = interpolate(selected, target)
                    audits.append({
                        "caseName": case, "channelType": channel,
                        "profileId": profile, "targetFER": target,
                        "interpolatedSnrDb": value, "status": status,
                        "leftSnrDb": left, "rightSnrDb": right,
                        "method": "LOG_FER_LINEAR_SNR",
                    })
                    loss_status = "VALID"
                    loss = ""
                    if awgn_status != "VALID" or status != "VALID":
                        loss_status = (status if status != "VALID" else awgn_status)
                    else:
                        loss = float(value) - float(awgn_snr)
                    losses.append({
                        "caseName": case, "channelType": channel,
                        "profileId": profile, "targetFER": target,
                        "channelSnrDb": value, "awgnSnrDb": awgn_snr,
                        "snrLossDb": loss, "status": loss_status,
                    })
    write(output_dir / "comparison_interpolation_audit.csv", audits)
    write(output_dir / "target_fer_snr_loss_summary.csv", losses)

    for source, target in [
        ("s2_05_residual_cfo/cfo_tolerance_summary.csv",
         "cfo_tolerance_summary.csv"),
        ("s2_06_short_blockage/blockage_tolerance_summary.csv",
         "blockage_tolerance_summary.csv"),
        ("s2_07_burst_sensitivity/burst_tolerance_summary.csv",
         "burst_tolerance_summary.csv"),
    ]:
        write(output_dir / target, read(stages / source))
    risk_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    for row in rows:
        risk_rows.append({
            "channelType": row["channelType"], "profileId": row["profileId"],
            "caseName": row["caseName"], "snrDb": row["snrDb"],
            "miscorrectionRate": row["miscorrectionRate"],
            "decoderFailureRate": row["decoderFailureRate"],
        })
        timing_rows.append({
            "channelType": row["channelType"], "profileId": row["profileId"],
            "caseName": row["caseName"], "snrDb": row["snrDb"],
            "avgDecodeTimeUs": row["avgDecodeTimeUs"],
            "avgTotalReceiverTimeUs": row["avgTotalReceiverTimeUs"],
        })
    write(output_dir / "miscorrection_risk_summary.csv", risk_rows)
    write(output_dir / "decoder_failure_risk_summary.csv", risk_rows)
    write(output_dir / "receiver_timing_summary.csv", timing_rows)
    print("PASS_BCH_S2_08_CHANNEL_ADAPTATION_COMPARISON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
