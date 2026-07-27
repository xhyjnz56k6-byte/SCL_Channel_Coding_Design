#!/usr/bin/env python3
"""Run the non-destructive BCH S2 scientific-semantics correction."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import run_bch_s2_batch2 as legacy


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"]
ROTATIONS = [0, 5, 10, 15, 20, 30, 45, 60, 75, 90, 120, 180]
PHASES = [0, 45, 90, 135]
TARGETS = (0.5, 0.1, 0.01)
RESULT_SUBTREE = "s2_batch2_corrected"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
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


def one_row(path: Path) -> dict[str, str]:
    rows = read_rows(path)
    if len(rows) != 1:
        raise RuntimeError(f"expected one row: {path}")
    return rows[0]


def execute_point(
    args: argparse.Namespace,
    repo: Path,
    channel: str,
    case: str,
    ebn0: float,
    frames: int,
    tag: str,
    extra: list[str],
    adaptive: bool = False,
) -> Path:
    result = repo / "Task/BCH/simulation/results" / RESULT_SUBTREE / tag
    summary = result / "summary.csv"
    if args.resume and summary.is_file():
        return summary
    result.mkdir(parents=True, exist_ok=True)
    payload = 200 if "200" in case else 300
    manifest = repo / (
        f"Task/BCH/simulation/results/frame_pools/formal_k{payload}/"
        f"k{payload}/manifest.json"
    )
    command = [
        str(repo / "Task/BCH/simulation/build/current/bch_impairment_runner.exe"),
        "--stage", "S2_SCIENTIFIC_CORRECTION",
        "--channel", channel,
        "--case", case,
        "--ebn0-db", str(ebn0),
        "--frame-start", "0",
        "--frame-count", str(frames),
        "--global-seed", str(args.global_seed),
        "--noise-policy-version", "2",
        "--frame-pool-manifest", str(manifest),
        "--output-dir", str(result),
        "--no-progress",
    ]
    if adaptive:
        command.extend([
            "--min-frames", "5000",
            "--target-frame-errors", "200",
            "--max-frames", "50000",
        ])
    command.extend(extra)
    subprocess.run(command, cwd=repo, check=True, stdout=subprocess.DEVNULL)
    return summary


def validate_rows(rows: list[dict[str, str]]) -> None:
    for row in rows:
        frames = int(row["processedFrames"])
        if int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != frames:
            raise SystemExit("BLOCKED_BCH_S2_TRUE_SUCCESS_ACCOUNTING")
        if int(row["reportedSuccessFrames"]) + int(row["decoderFailureFrames"]) != frames:
            raise SystemExit("BLOCKED_BCH_S2_REPORTED_SUCCESS_ACCOUNTING")
        if float(row["initialPhaseDeg"]) != 0.0 and row.get(
            "resultClass"
        ) == "RESIDUAL_CFO_PHI0_ZERO":
            raise SystemExit("BLOCKED_BCH_S2_CORRECTED_CFO_PHASE_CONTAMINATION")
        for field in (
            "BER", "FER", "avgDecodeTimeUs", "avgTotalReceiverTimeUs",
            "medianReceiverTimeUs", "p95ReceiverTimeUs", "p99ReceiverTimeUs",
        ):
            if not math.isfinite(float(row[field])):
                raise SystemExit(f"BLOCKED_BCH_S2_NONFINITE_{field}")


def publish(
    stage: Path, published: Path, name: str, rows: list[dict[str, object]],
) -> None:
    write_rows(stage / name, rows)
    write_rows(published / name, rows)


def run_corrected_cfo(
    args: argparse.Namespace,
    repo: Path,
    awgn: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    paths: list[Path] = []
    for case in CASES:
        for snr_index, ebn0 in enumerate(legacy.awgn_references(awgn, case)):
            for rotation in ROTATIONS:
                tag = (
                    f"s2_05/main_phi0_zero/{legacy.case_slug(case)}_"
                    f"s{snr_index}_r{rotation}"
                )
                paths.append(execute_point(
                    args, repo, "RESIDUAL_CFO", case, ebn0, 5000, tag,
                    ["--initial-phase-deg", "0",
                     "--frame-rotation-deg", str(rotation)],
                ))
    main_rows = [one_row(path) for path in paths]
    for row in main_rows:
        row["resultClass"] = "RESIDUAL_CFO_PHI0_ZERO"
        row["experimentAxis"] = "FRAME_ROTATION"
        row["physicalFrequencyNote"] = (
            "FRAME_TOTAL_ROTATION;SAME_ANGLE_IS_NOT_SAME_NORMALIZED_CFO"
        )
    validate_rows(main_rows)

    snr_paths: list[Path] = []
    for case in CASES:
        refs = legacy.awgn_references(awgn, case)
        for rotation in (30, 60):
            for ebn0 in legacy.grid(min(refs[:2]) - 1.0, max(refs[:2]) + 1.0):
                tag = (
                    f"s2_05/snr_phi0_zero/{legacy.case_slug(case)}_"
                    f"r{rotation}_e{ebn0:.1f}"
                )
                snr_paths.append(execute_point(
                    args, repo, "RESIDUAL_CFO", case, ebn0, 50000, tag,
                    ["--initial-phase-deg", "0",
                     "--frame-rotation-deg", str(rotation)],
                    adaptive=True,
                ))
    snr_rows = [one_row(path) for path in snr_paths]
    for row in snr_rows:
        row["resultClass"] = "RESIDUAL_CFO_PHI0_ZERO"
        row["experimentAxis"] = "SNR"
    validate_rows(snr_rows)

    phase_paths: list[Path] = []
    for case in CASES:
        ebn0 = sorted(legacy.awgn_references(awgn, case))[1]
        for rotation in (0, 30):
            for phase in PHASES:
                tag = (
                    f"s2_05/initial_phase_sensitivity/{legacy.case_slug(case)}_"
                    f"r{rotation}_p{phase}"
                )
                phase_paths.append(execute_point(
                    args, repo, "RESIDUAL_CFO", case, ebn0, 5000, tag,
                    ["--initial-phase-deg", str(phase),
                     "--frame-rotation-deg", str(rotation)],
                ))
    phase_rows = [one_row(path) for path in phase_paths]
    for row in phase_rows:
        row["resultClass"] = "INITIAL_PHASE_SENSITIVITY"
        row["experimentAxis"] = "INITIAL_PHASE"
    validate_rows(phase_rows)
    return main_rows + snr_rows, phase_rows


def run_corrected_timing(
    args: argparse.Namespace,
    repo: Path,
    awgn: list[dict[str, str]],
) -> list[dict[str, str]]:
    paths: list[Path] = []
    for case in CASES:
        ebn0 = sorted(legacy.awgn_references(awgn, case))[1]
        for rotation in (30, 60):
            tag = (
                f"s2_08/timing_audit_v2/{legacy.case_slug(case)}_"
                f"cfo_{rotation}"
            )
            paths.append(execute_point(
                args, repo, "RESIDUAL_CFO", case, ebn0, 5000, tag,
                ["--initial-phase-deg", "0",
                 "--frame-rotation-deg", str(rotation)],
            ))
        for profile, attenuation, length in (
            ("M", -12, 16),
            ("H", -20, 32),
        ):
            tag = (
                f"s2_08/timing_audit_v2/{legacy.case_slug(case)}_"
                f"blockage_{profile}"
            )
            paths.append(execute_point(
                args, repo, "SHORT_BLOCKAGE", case, ebn0, 5000, tag,
                ["--attenuation-db", str(attenuation),
                 "--blockage-length", str(length),
                 "--blockage-start-policy", "UNIFORM_RANDOM"],
            ))
    rows = [one_row(path) for path in paths]
    for row in rows:
        row["timingAuditClass"] = (
            "CFO_TIMING_ONLY_NO_BER_FER_REPLACEMENT"
            if row["channelType"] == "RESIDUAL_CFO"
            else "BLOCKAGE_TIMING_ONLY_NO_BER_FER_REPLACEMENT"
        )
    validate_rows(rows)
    return rows


def run_awgn_timing_audit(
    args: argparse.Namespace,
    repo: Path,
    awgn: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in CASES:
        ebn0 = sorted(legacy.awgn_references(awgn, case))[1]
        payload = 200 if "200" in case else 300
        result = (
            repo / "Task/BCH/simulation/results" / RESULT_SUBTREE
            / "s2_08/timing_audit_awgn" / legacy.case_slug(case)
        )
        summary = result / "summary.csv"
        if not (args.resume and summary.is_file()):
            result.mkdir(parents=True, exist_ok=True)
            manifest = repo / (
                f"Task/BCH/simulation/results/frame_pools/formal_k{payload}/"
                f"k{payload}/manifest.json"
            )
            subprocess.run([
                str(repo / "Task/BCH/simulation/build/current/bch_awgn_runner.exe"),
                "--stage", "S2_SCIENTIFIC_CORRECTION_TIMING",
                "--case", case,
                "--ebn0-db", str(ebn0),
                "--snr-index", "0",
                "--frame-start", "0",
                "--frame-count", "5000",
                "--global-seed", str(args.global_seed),
                "--frame-pool-manifest", str(manifest),
                "--output-dir", str(result),
                "--timing-warmup-frames", "500",
                "--no-progress",
            ], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        row = one_row(summary)
        row["timingAuditClass"] = "AWGN_TIMING_ONLY_NO_BER_FER_REPLACEMENT"
        rows.append(row)
    return rows


def run_burst_theory_points(
    args: argparse.Namespace,
    repo: Path,
) -> list[dict[str, str]]:
    guaranteed = {
        "BCH-S200": 1,
        "BCH-S300": 1,
        "BCH-B200": 6,
        "BCH-B300": 10,
        "BCH-B300-426": 14,
    }
    paths: list[Path] = []
    for case, maximum in guaranteed.items():
        for length in range(1, maximum + 1):
            for start in legacy.STARTS_BURST:
                tag = (
                    f"s2_07/theory_gate/{legacy.case_slug(case)}_"
                    f"l{length}_{start.lower()}"
                )
                paths.append(execute_point(
                    args, repo, "BURST", case, 0.0, 5000, tag,
                    ["--burst-mode", "PURE",
                     "--burst-length", str(length),
                     "--burst-start-policy", start],
                ))
    rows = [one_row(path) for path in paths]
    validate_rows(rows)
    return rows


def classify_curve(
    values: list[dict[str, str]],
    parameter: str,
    target: float,
) -> dict[str, object]:
    points = sorted(
        [(float(row[parameter]), float(row["FER"])) for row in values],
        key=lambda item: item[0],
    )
    if len({point[0] for point in points}) != len(points):
        raise RuntimeError("threshold curve contains duplicate parameter values")
    p_min, fer_min = points[0]
    p_max, fer_max = points[-1]
    exact = [point for point in points if abs(point[1] - target) <= 1e-15]
    crossings = [
        (left, right)
        for left, right in zip(points, points[1:])
        if (left[1] - target) * (right[1] - target) < 0.0
    ]
    upward = [
        pair for pair in crossings
        if pair[0][1] <= target and pair[1][1] > target
    ]
    base: dict[str, object] = {
        "targetFER": target,
        "parameter": parameter,
        "maximumToleratedParameter": "",
        "lowerBound": "",
        "upperBound": "",
        "numberOfCrossings": len(crossings),
        "firstCrossing": (
            f"{crossings[0][0][0]}..{crossings[0][1][0]}" if crossings else ""
        ),
        "lastCrossing": (
            f"{crossings[-1][0][0]}..{crossings[-1][1][0]}" if crossings else ""
        ),
        "method": "OBSERVED_POINTS_NO_SMOOTHING_NO_EXTRAPOLATION",
    }
    if len(crossings) > 1:
        base["status"] = "NON_MONOTONIC_NO_UNIQUE_THRESHOLD"
    elif exact:
        base.update({
            "maximumToleratedParameter": exact[0][0],
            "lowerBound": exact[0][0],
            "upperBound": exact[0][0],
            "status": "EXACT_OBSERVED_POINT",
        })
    elif fer_min > target:
        base.update({
            "upperBound": p_min,
            "status": "BELOW_MINIMUM_TESTED_PARAMETER",
        })
    elif fer_max <= target:
        base.update({
            "lowerBound": p_max,
            "status": "LOWER_BOUND_AT_TEST_LIMIT",
        })
    elif upward:
        base.update({
            "lowerBound": upward[0][0][0],
            "upperBound": upward[0][1][0],
            "status": "BRACKETED_INTERVAL",
        })
    else:
        base["status"] = "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION"
    return base


def tolerance_summary(
    rows: list[dict[str, str]],
    parameter: str,
    group_fields: list[str],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in group_fields), []).append(row)
    output: list[dict[str, object]] = []
    for key, values in sorted(groups.items()):
        for target in TARGETS:
            record = dict(zip(group_fields, key))
            record.update(classify_curve(values, parameter, target))
            output.append(record)
    return output


def burst_theory_gate(
    rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    guaranteed = {
        "BCH-S200": 1,
        "BCH-S300": 1,
        "BCH-B200": 6,
        "BCH-B300": 10,
        "BCH-B300-426": 14,
    }
    output: list[dict[str, object]] = []
    for case, maximum in guaranteed.items():
        selected = [
            row for row in rows
            if row["caseName"] == case
            and int(row["burstLength"]) <= maximum
        ]
        expected = maximum * len(legacy.STARTS_BURST)
        failures = sum(int(row["decodedFrameErrors"]) for row in selected)
        status = "PASS" if len(selected) == expected and failures == 0 else "BLOCKED"
        output.append({
            "caseName": case,
            "guaranteedBurstLengthMax": maximum,
            "testedPointCount": len(selected),
            "expectedPointCount": expected,
            "decodedFrameErrors": failures,
            "status": status,
        })
    if any(row["status"] != "PASS" for row in output):
        raise SystemExit(
            "BLOCKED_BCH_S2_BURST_GUARANTEED_CORRECTION_VIOLATION"
        )
    return output


def write_stage_records(
    repo: Path,
    cfo_rows: list[dict[str, str]],
    phase_rows: list[dict[str, str]],
    timing_rows: list[dict[str, str]],
    awgn_timing_rows: list[dict[str, str]],
    burst_theory_rows: list[dict[str, str]],
) -> None:
    stages = repo / "Task/BCH/simulation/stages"
    cfo_stage = stages / "s2_05_residual_cfo_corrected"
    comparison_stage = stages / "s2_08_channel_adaptation_comparison_corrected"
    published = repo / "Task/BCH/simulation/results" / RESULT_SUBTREE / "published"
    cfo_stage.mkdir(parents=True, exist_ok=True)
    comparison_stage.mkdir(parents=True, exist_ok=True)

    main_rows = [
        row for row in cfo_rows
        if row["experimentAxis"] == "FRAME_ROTATION"
    ]
    snr_rows = [row for row in cfo_rows if row["experimentAxis"] == "SNR"]
    publish(cfo_stage, published / "s2_05", "cfo_phi0_zero_summary.csv", main_rows)
    publish(cfo_stage, published / "s2_05", "cfo_phi0_zero_snr_summary.csv", snr_rows)
    publish(
        cfo_stage, published / "s2_05",
        "initial_phase_sensitivity_summary.csv", phase_rows,
    )
    publish(
        comparison_stage, published / "s2_08",
        "impairment_receiver_timing_audit.csv", timing_rows,
    )
    publish(
        comparison_stage, published / "s2_08",
        "awgn_receiver_timing_audit.csv", awgn_timing_rows,
    )
    cfo_tolerance = tolerance_summary(
        main_rows, "frameRotationDeg",
        ["caseName", "sourcePayloadEbN0Db", "initialPhaseDeg"],
    )
    publish(
        comparison_stage, published / "s2_08",
        "cfo_tolerance_summary.csv", cfo_tolerance,
    )

    blockage = read_rows(
        stages / "s2_06_short_blockage/blockage_formal_parameter_summary.csv"
    )
    blockage_tolerance = tolerance_summary(
        blockage, "blockageLength",
        ["caseName", "sourcePayloadEbN0Db", "attenuationDb",
         "completeBlockage", "blockageStartPolicy"],
    )
    publish(
        comparison_stage, published / "s2_08",
        "blockage_tolerance_summary.csv", blockage_tolerance,
    )

    burst = read_rows(stages / "s2_07_burst_sensitivity/formal_summary.csv")
    burst_tolerance = tolerance_summary(
        burst, "burstLength",
        ["caseName", "burstMode", "sourcePayloadEbN0Db", "burstStartPolicy"],
    )
    publish(
        comparison_stage, published / "s2_08",
        "burst_tolerance_summary.csv", burst_tolerance,
    )
    publish(
        comparison_stage, published / "s2_08",
        "pure_burst_guaranteed_region_summary.csv", burst_theory_rows,
    )
    theory = burst_theory_gate(burst_theory_rows)
    publish(
        comparison_stage, published / "s2_08",
        "burst_theory_gate.csv", theory,
    )
    status_counts = Counter(
        row["status"]
        for row in cfo_tolerance + blockage_tolerance + burst_tolerance
    )
    publish(
        comparison_stage, published / "s2_08",
        "tolerance_status_counts.csv",
        [{"status": status, "count": count}
         for status, count in sorted(status_counts.items())],
    )

    shutil.copy2(
        stages / "s2_06_short_blockage/blockage_formal_snr_summary.csv",
        published / "s2_08/blockage_formal_snr_summary.csv",
    )
    shutil.copy2(
        stages / "s2_07_burst_sensitivity/pure_burst_summary.csv",
        published / "s2_08/pure_burst_summary.csv",
    )
    shutil.copy2(
        stages / "s2_07_burst_sensitivity/awgn_burst_summary.csv",
        published / "s2_08/awgn_burst_summary.csv",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--postprocess-only", action="store_true")
    parser.add_argument("--global-seed", type=int, default=legacy.SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[4]
    baseline = legacy.baseline_audit(repo, write_output=False)
    if not args.postprocess_only:
        subprocess.run(
            ["cmake", "--build", "Task/BCH/simulation/build/current",
             "--config", "Release", "-j", "4"],
            cwd=repo, check=True,
        )
        subprocess.run(
            ["ctest", "--test-dir", "Task/BCH/simulation/build/current",
             "-C", "Release", "--output-on-failure",
             "-R", "bch_s2_impairments_unit"],
            cwd=repo, check=True,
        )
        cfo_rows, phase_rows = run_corrected_cfo(
            args, repo, baseline["awgn"]
        )
        timing_rows = run_corrected_timing(args, repo, baseline["awgn"])
        awgn_timing_rows = run_awgn_timing_audit(
            args, repo, baseline["awgn"]
        )
        burst_theory_rows = run_burst_theory_points(args, repo)
    else:
        root = repo / "Task/BCH/simulation/results" / RESULT_SUBTREE / "s2_05"
        main_paths = list((root / "main_phi0_zero").glob("*/summary.csv"))
        snr_paths = list((root / "snr_phi0_zero").glob("*/summary.csv"))
        cfo_rows = [one_row(path) for path in main_paths + snr_paths]
        phase_rows = [
            one_row(path)
            for path in (root / "initial_phase_sensitivity").glob("*/summary.csv")
        ]
        timing_rows = [
            one_row(path)
            for path in (
                repo / "Task/BCH/simulation/results" / RESULT_SUBTREE
                / "s2_08/timing_audit_v2"
            ).glob("*/summary.csv")
        ]
        awgn_timing_rows = [
            one_row(path)
            for path in (
                repo / "Task/BCH/simulation/results" / RESULT_SUBTREE
                / "s2_08/timing_audit_awgn"
            ).glob("*/summary.csv")
        ]
        burst_theory_rows = [
            one_row(path)
            for path in (
                repo / "Task/BCH/simulation/results" / RESULT_SUBTREE
                / "s2_07/theory_gate"
            ).glob("*/summary.csv")
        ]
        for index, row in enumerate(cfo_rows):
            row["resultClass"] = "RESIDUAL_CFO_PHI0_ZERO"
            row["experimentAxis"] = (
                "FRAME_ROTATION" if index < len(main_paths) else "SNR"
            )
        for row in phase_rows:
            row["resultClass"] = "INITIAL_PHASE_SENSITIVITY"
            row["experimentAxis"] = "INITIAL_PHASE"
    write_stage_records(
        repo, cfo_rows, phase_rows, timing_rows, awgn_timing_rows,
        burst_theory_rows
    )
    print("PASS_BCH_S2_CFO_PHI0_ZERO_CORRECTED")
    print("PASS_BCH_S2_STRICT_TOLERANCE_CLASSIFICATION")
    print("PASS_BCH_S2_BURST_THEORY_GATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
