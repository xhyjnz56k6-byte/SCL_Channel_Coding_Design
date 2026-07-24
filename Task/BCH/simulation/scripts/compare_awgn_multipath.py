#!/usr/bin/env python3
"""Strict AWGN/multipath comparison with bracketed log-FER interpolation."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


TARGETS = [1e-1, 1e-2, 1e-3]


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def bracketed(curve: list[dict[str, str]], target: float) -> tuple[float | None, str, str, str]:
    ordered = sorted(curve, key=lambda row: float(row["snrDb"]))
    candidates: list[tuple[dict[str, str], dict[str, str]]] = []
    for lower, upper in zip(ordered, ordered[1:]):
        f1, f2 = float(lower["FER"]), float(upper["FER"])
        if f1 > 0.0 and f2 > 0.0 and (f1 - target) * (f2 - target) <= 0.0:
            candidates.append((lower, upper))
    if not candidates:
        return None, "", "", "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION"
    lower, upper = candidates[0]
    x1, x2 = float(lower["snrDb"]), float(upper["snrDb"])
    y1, y2 = math.log10(float(lower["FER"])), math.log10(float(upper["FER"]))
    if abs(y2 - y1) < 1e-15:
        value = (x1 + x2) / 2.0
    else:
        value = x1 + (math.log10(target) - y1) * (x2 - x1) / (y2 - y1)
    return value, f"{x1:.17g};{float(lower['FER']):.17g}", \
        f"{x2:.17g};{float(upper['FER']):.17g}", "PASS"


def interpolate_positive(curve: list[dict[str, str]], snr: float) -> tuple[float | None, str]:
    ordered = sorted(curve, key=lambda row: float(row["snrDb"]))
    for row in ordered:
        if abs(float(row["snrDb"]) - snr) < 1e-12:
            fer = float(row["FER"])
            return (fer, "EXACT") if fer > 0.0 else (None, "UNDEFINED_AWGN_ZERO_OBSERVATION")
    for lower, upper in zip(ordered, ordered[1:]):
        x1, x2 = float(lower["snrDb"]), float(upper["snrDb"])
        if x1 < snr < x2:
            f1, f2 = float(lower["FER"]), float(upper["FER"])
            if f1 == 0.0 or f2 == 0.0:
                return None, "UNDEFINED_AWGN_ZERO_OBSERVATION"
            value = 10 ** (math.log10(f1) + (snr - x1) *
                           (math.log10(f2) - math.log10(f1)) / (x2 - x1))
            return value, "BRACKETED_LOG_INTERPOLATION"
    return None, "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/s2_04_fixed_multipath_mmse"
    multipath = read(stage / "formal_summary.csv")
    awgn = read(repo / "Task/BCH/simulation/stages/s2_03_awgn_baseline_reuse/awgn_baseline_snr_converted.csv")
    cases = sorted({row["caseName"] for row in multipath})
    by_multi = {case: [row for row in multipath if row["caseName"] == case] for case in cases}
    by_awgn = {case: [row for row in awgn if row["caseName"] == case] for case in cases}

    interpolation: list[dict[str, object]] = []
    loss: list[dict[str, object]] = []
    for case in cases:
        for target in TARGETS:
            awgn_snr, awgn_low, awgn_high, awgn_reason = bracketed(by_awgn[case], target)
            multi_snr, multi_low, multi_high, multi_reason = bracketed(by_multi[case], target)
            valid = awgn_snr is not None and multi_snr is not None
            reason = "PASS" if valid else f"AWGN:{awgn_reason};MULTIPATH:{multi_reason}"
            row = {
                "caseName": case, "targetFer": target,
                "awgnLowerBracket": awgn_low, "awgnUpperBracket": awgn_high,
                "multipathLowerBracket": multi_low, "multipathUpperBracket": multi_high,
                "awgnInterpolatedSnrDb": "" if awgn_snr is None else f"{awgn_snr:.17g}",
                "multipathInterpolatedSnrDb": "" if multi_snr is None else f"{multi_snr:.17g}",
                "multipathLossDb": "" if not valid else f"{multi_snr - awgn_snr:.17g}",
                "valid": str(valid).lower(), "reason": reason,
            }
            interpolation.append(row)
            loss.append(dict(row))
    write(stage / "awgn_multipath_interpolation_audit.csv", interpolation)
    write(stage / "multipath_loss_summary.csv", loss)

    amplification: list[dict[str, object]] = []
    for case in cases:
        for row in by_multi[case]:
            snr = float(row["snrDb"])
            awgn_fer, reason = interpolate_positive(by_awgn[case], snr)
            valid = awgn_fer is not None
            amplification.append({
                "caseName": case, "snrDb": row["snrDb"],
                "multipathFer": row["FER"],
                "awgnFer": "" if awgn_fer is None else f"{awgn_fer:.17g}",
                "ferAmplification": "" if not valid else f"{float(row['FER']) / awgn_fer:.17g}",
                "valid": str(valid).lower(), "reason": reason,
            })
    write(stage / "fer_amplification_summary.csv", amplification)

    mmse = [{
        "caseName": row["caseName"], "snrDb": row["snrDb"],
        "preEqHardBER": row["preEqualizationHardBER"],
        "postEqHardBER": row["postEqualizationHardBER"],
        "mmseHardBerReductionRatio": (
            "" if float(row["preEqualizationHardBER"]) == 0.0 else
            f"{float(row['postEqualizationHardBER']) / float(row['preEqualizationHardBER']):.17g}"
        ),
        "valid": str(float(row["preEqualizationHardBER"]) > 0.0).lower(),
    } for row in multipath]
    write(stage / "mmse_hard_ber_summary.csv", mmse)

    timing: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in multipath:
        grouped[row["caseName"]].append(row)
    for case, rows in sorted(grouped.items()):
        frames = sum(int(row["processedFrames"]) for row in rows)
        weighted = lambda field: sum(float(row[field]) * int(row["processedFrames"]) for row in rows) / frames
        timing.append({
            "caseName": case, "processedFrames": frames,
            "avgEqualizationTimeUs": f"{weighted('avgEqualizationTimeUs'):.17g}",
            "avgDecodeTimeUs": f"{weighted('avgDecodeTimeUs'):.17g}",
            "avgTotalReceiverTimeUs": f"{weighted('avgTotalReceiverTimeUs'):.17g}",
            "maxP95EqualizationTimeUs": max(float(row["p95EqualizationTimeUs"]) for row in rows),
            "maxP99EqualizationTimeUs": max(float(row["p99EqualizationTimeUs"]) for row in rows),
            "maxP95DecodeTimeUs": max(float(row["p95DecodeTimeUs"]) for row in rows),
            "maxP99DecodeTimeUs": max(float(row["p99DecodeTimeUs"]) for row in rows),
        })
    write(stage / "timing_summary.csv", timing)
    print("PASS_BCH_S2_04_AWGN_MULTIPATH_COMPARISON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
