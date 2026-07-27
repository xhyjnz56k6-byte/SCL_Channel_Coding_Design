#!/usr/bin/env python3
"""One-entry driver for BCH S2-05..S2-09 channel-adaptation experiments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path


CASES = ["BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"]
PHASES = [0.0, 45.0, 90.0, 135.0]
STARTS_BLOCKAGE = [
    "FRAME_START", "FRAME_MIDDLE", "FRAME_END", "SEGMENT_INTERIOR",
    "ONE_BEFORE_SEGMENT_BOUNDARY", "ON_SEGMENT_BOUNDARY", "UNIFORM_RANDOM",
]
STARTS_BURST = [
    "FRAME_START", "FRAME_END", "SEGMENT_INTERIOR",
    "ONE_BEFORE_SEGMENT_BOUNDARY", "ON_SEGMENT_BOUNDARY", "UNIFORM_RANDOM",
]
STAGE_NAMES = {
    "s2_05": "s2_05_residual_cfo",
    "s2_06": "s2_06_short_blockage",
    "s2_07": "s2_07_burst_sensitivity",
    "s2_08": "s2_08_channel_adaptation_comparison",
    "s2_09": "s2_09_matlab_channel_reference",
}
SEED = 2026072601


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=check, text=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
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


def payload(case: str) -> int:
    return 200 if "200" in case else 300


def case_slug(case: str) -> str:
    return case.lower().replace("-", "_")


def grid(low: float, high: float, step: float = 0.2) -> list[float]:
    count = int(round((high - low) / step))
    return [round(low + index * step, 10) for index in range(count + 1)]


def initialize_stage_records(repo: Path) -> None:
    stage_root = repo / "Task/BCH/simulation/stages"
    descriptions = {
        "s2_05": ("残余频偏", "复基带 CFO、理想补偿验证与无补偿敏感性"),
        "s2_06": ("短时遮挡", "衰减、长度与绝对起点策略敏感性"),
        "s2_07": ("突发错误", "纯 burst 与 AWGN 后硬判决连续翻转"),
        "s2_08": ("多信道综合比较", "只复用既有 AWGN/多径基线并纳入新信道"),
        "s2_09": ("MATLAB 独立参考", "独立复算 CFO、遮挡和 burst 代表点"),
    }
    for key, directory in STAGE_NAMES.items():
        stage = stage_root / directory
        stage.mkdir(parents=True, exist_ok=True)
        title, goal = descriptions[key]
        matrix = [
            {
                "需求": goal,
                "实现位置": f"Task/BCH/simulation/stages/{directory}",
                "正向测试": "C++ unit/smoke/formal/reference",
                "负向测试": "invalid config/hash/range rejection",
                "Gate条件": f"PASS_BCH_{key.upper()}",
            }
        ]
        write_rows(stage / "acceptance_matrix.csv", matrix)
        (stage / "stage_plan.md").write_text(
            f"# {directory}\n\n## 目标\n\n{goal}。\n\n"
            "## 非目标\n\n不修改 BCH 核心编译码器；不重跑 AWGN 或固定多径 formal；"
            "不引入交织、软判决 BCH、卷积码或 LDPC。\n\n"
            "## 范围\n\n仅限 Task/BCH 本 Stage 的信道基础、runner、脚本、测试、"
            "小型结果、科研绘图和审计记录。\n\n"
            "## 接口与数据\n\n统一使用 sourcePayloadEbN0Db、frameRate、snrDb；"
            "snrDb=sourcePayloadEbN0Db+10*log10(frameRate)，Bn=Rs；"
            "noisePolicyVersion=2。\n\n"
            "## Gate\n\n必须通过正向、负向、统计恒等式和数据审计后才发布 Gate。\n",
            encoding="utf-8",
        )
        write_rows(stage / "frozen_config.csv", [
            {"key": "stage", "value": directory},
            {"key": "title", "value": title},
            {"key": "noisePolicyVersion", "value": 2},
            {"key": "bandwidthConvention", "value": "Bn_EQUALS_Rs"},
            {"key": "xTransformFormula",
             "value": "snrDb=sourcePayloadEbN0Db+10*log10(frameRate)"},
            {"key": "globalSeed", "value": SEED},
        ])


def baseline_audit(
    repo: Path, write_output: bool = True,
) -> dict[str, list[dict[str, str]]]:
    awgn_index = repo / "Task/BCH/simulation/stages/s2_03_awgn_baseline_reuse/awgn_baseline_sources.csv"
    multipath = repo / "Task/BCH/simulation/stages/s2_04_fixed_multipath_mmse/formal_summary.csv"
    if not awgn_index.is_file() or not multipath.is_file():
        raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")
    awgn_sources = read_rows(awgn_index)
    output: list[dict[str, object]] = []
    all_awgn: list[dict[str, str]] = []
    for source in awgn_sources:
        source_path = repo / source["sourcePath"]
        if sha256(source_path) != source["sourceSha256"]:
            raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")
        rows = [row for row in read_rows(source_path)
                if row.get("caseName") == source["caseName"]]
        if len(rows) != int(source["pointCount"]):
            raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")
        all_awgn.extend(rows)
        output.append({
            "channelType": "AWGN",
            "caseName": source["caseName"],
            "sourceCommit": source["sourceGitCommit"],
            "sourcePath": source["sourcePath"],
            "sourceSha256": source["sourceSha256"],
            "pointCount": source["pointCount"],
            "totalFrames": source["processedFrames"],
            "payloadLength": source["payloadLength"],
            "encodedLength": source["encodedLength"],
            "frameRate": source["frameRate"],
            "snrMin": source["snrMin"],
            "snrMax": source["snrMax"],
            "schemaVersion": source["schemaVersion"],
            "reuseStatus": "REUSED_S1_FORMAL_AWGN_BASELINE",
        })
    multipath_rows = read_rows(multipath)
    multipath_hash = sha256(multipath)
    for case in CASES:
        rows = [row for row in multipath_rows if row["caseName"] == case]
        if not rows:
            raise SystemExit("BLOCKED_BCH_S2_BASELINE_REUSE_MISMATCH")
        output.append({
            "channelType": "MULTIPATH_MMSE",
            "caseName": case,
            "sourceCommit": "069373b02401ad0acc10d96eb4e63bad8763c64c",
            "sourcePath": str(multipath.relative_to(repo)).replace("\\", "/"),
            "sourceSha256": multipath_hash,
            "pointCount": len(rows),
            "totalFrames": sum(int(row["processedFrames"]) for row in rows),
            "payloadLength": rows[0]["payloadLength"],
            "encodedLength": rows[0]["encodedLength"],
            "frameRate": rows[0]["frameRate"],
            "snrMin": min(float(row["snrDb"]) for row in rows),
            "snrMax": max(float(row["snrDb"]) for row in rows),
            "schemaVersion": rows[0]["schemaVersion"],
            "reuseStatus": "REUSED_S2_04_FIXED_MULTIPATH_MMSE",
        })
    if write_output:
        comparison = repo / "Task/BCH/simulation/stages/s2_08_channel_adaptation_comparison"
        write_rows(comparison / "baseline_sources.csv", output)
    return {"awgn": all_awgn, "multipath": multipath_rows}


def awgn_references(rows: list[dict[str, str]], case: str) -> list[float]:
    candidates = [row for row in rows if row["caseName"] == case]
    if not candidates:
        raise RuntimeError(f"missing AWGN baseline for {case}")
    eb_field = next(
        field for field in ("sourcePayloadEbN0Db", "sourceEbN0Db", "ebn0Db")
        if field in candidates[0]
    )
    chosen = []
    for target in (0.1, 0.01):
        positive = [row for row in candidates if float(row["FER"]) > 0.0]
        chosen.append(float(min(
            positive,
            key=lambda row: abs(math.log10(float(row["FER"])) - math.log10(target)),
        )[eb_field]))
    chosen.append(max(float(row[eb_field]) for row in candidates))
    return chosen


def execute_point(
    args: argparse.Namespace,
    repo: Path,
    stage_key: str,
    channel: str,
    case: str,
    ebn0: float,
    frames: int,
    tag: str,
    extra: list[str],
    adaptive: bool = False,
) -> Path:
    result = repo / "Task/BCH/simulation/results/s2_batch2" / stage_key / tag
    summary = result / "summary.csv"
    if args.resume and summary.is_file():
        return summary
    result.mkdir(parents=True, exist_ok=True)
    manifest = repo / (
        f"Task/BCH/simulation/results/frame_pools/formal_k{payload(case)}/"
        f"k{payload(case)}/manifest.json"
    )
    command = [
        str(repo / "Task/BCH/simulation/build/current/bch_impairment_runner.exe"),
        "--stage", stage_key.upper(), "--channel", channel, "--case", case,
        "--ebn0-db", str(ebn0), "--frame-start", "0", "--frame-count", str(frames),
        "--global-seed", str(args.global_seed), "--noise-policy-version", "2",
        "--frame-pool-manifest", str(manifest), "--output-dir", str(result),
        "--progress-refresh-seconds", str(args.progress_refresh_seconds),
        "--progress" if args.progress else "--no-progress",
    ]
    if adaptive:
        command.extend([
            "--min-frames", "5000", "--target-frame-errors", "200",
            "--max-frames", "50000",
        ])
    command.extend(extra)
    subprocess.run(command, cwd=repo, check=True, text=True,
                   stdout=subprocess.DEVNULL)
    return summary


def aggregate(stage: Path, name: str, paths: list[Path]) -> list[dict[str, str]]:
    rows = [one_row(path) for path in paths]
    for row in rows:
        frames = int(row["processedFrames"])
        if (int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != frames or
                int(row["reportedSuccessFrames"]) +
                int(row["decoderFailureFrames"]) != frames):
            raise SystemExit("BLOCKED_BCH_S2_METRIC_INCONSISTENCY")
        expected = float(row["sourcePayloadEbN0Db"]) + 10.0 * math.log10(
            float(row["frameRate"]))
        if abs(expected - float(row["snrDb"])) > 5e-10:
            raise SystemExit("BLOCKED_BCH_S2_SNR_SEMANTIC_MISMATCH")
    write_rows(stage / name, rows)
    return rows


def run_cfo_smoke(args: argparse.Namespace, repo: Path, awgn: list[dict[str, str]]) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_05_residual_cfo"
    paths: list[Path] = []
    started = time.monotonic()
    rotations = [0, 10, 30, 60, 90, 120, 180]
    for case in CASES:
        for snr_index, ebn0 in enumerate(awgn_references(awgn, case)):
            for rotation in rotations:
                for phase in PHASES:
                    tag = (f"smoke/{case_slug(case)}_s{snr_index}_"
                           f"r{rotation}_p{int(phase)}")
                    paths.append(execute_point(
                        args, repo, "s2_05", "RESIDUAL_CFO", case, ebn0, 500, tag,
                        ["--initial-phase-deg", str(phase),
                         "--frame-rotation-deg", str(rotation)],
                    ))
    rows = aggregate(stage, "smoke_summary.csv", paths)
    trend: list[dict[str, object]] = []
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["caseName"], row["sourcePayloadEbN0Db"],
                            row["frameRotationDeg"]), []).append(row)
    for key, values in grouped.items():
        trend.append({
            "caseName": key[0], "sourcePayloadEbN0Db": key[1],
            "frameRotationDeg": key[2],
            "processedFrames": sum(int(row["processedFrames"]) for row in values),
            "decodedFrameErrors": sum(int(row["decodedFrameErrors"]) for row in values),
            "FER": sum(int(row["decodedFrameErrors"]) for row in values) /
                   sum(int(row["processedFrames"]) for row in values),
            "aggregation": "RAW_COUNTS_OVER_FOUR_PHASES",
        })
    write_rows(stage / "smoke_phase_trend.csv", trend)
    write_rows(stage / "formal_parameter_recommendation.csv", [
        {"caseName": case, "formalARotations": "0;5;10;15;20;30;45;60;75;90;120;180",
         "formalBRotations": "30;60", "formalBSnrStepDb": 0.2}
        for case in CASES
    ])
    write_rows(stage / "smoke_runtime_estimate.csv", [{
        "smokePoints": len(rows),
        "smokeFrames": sum(int(row["processedFrames"]) for row in rows),
        "elapsedSeconds": time.monotonic() - started,
    }])
    print("PASS_BCH_S2_05_SMOKE")


def run_blockage_smoke(args: argparse.Namespace, repo: Path, awgn: list[dict[str, str]]) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_06_short_blockage"
    paths: list[Path] = []
    started = time.monotonic()
    attenuations = [(-6, False), (-12, False), (-20, False), (0, True)]
    lengths = [1, 8, 15, 16, 32, 64]
    for case in CASES:
        for snr_index, ebn0 in enumerate(awgn_references(awgn, case)[:2]):
            for attenuation, complete in attenuations:
                for length in lengths:
                    for start in STARTS_BLOCKAGE:
                        profile = "complete" if complete else f"m{abs(attenuation)}"
                        tag = (f"smoke/{case_slug(case)}_s{snr_index}_{profile}_"
                               f"l{length}_{start.lower()}")
                        extra = [
                            "--attenuation-db", str(attenuation),
                            "--blockage-length", str(length),
                            "--blockage-start-policy", start,
                        ]
                        if complete:
                            extra.append("--complete-blockage")
                        paths.append(execute_point(
                            args, repo, "s2_06", "SHORT_BLOCKAGE", case,
                            ebn0, 500, tag, extra,
                        ))
    rows = aggregate(stage, "smoke_summary.csv", paths)
    write_rows(stage / "formal_parameter_recommendation.csv", [
        {"caseName": case, "formalAttenuationsDb": "0;-6;-12;-20;COMPLETE",
         "formalLengths": "1;2;4;6;8;10;12;14;15;16;20;24;29;30;31;32;48;64",
         "formalProfiles": "M:-12dB,length16;H:-20dB,length32"}
        for case in CASES
    ])
    write_rows(stage / "smoke_runtime_estimate.csv", [{
        "smokePoints": len(rows),
        "smokeFrames": sum(int(row["processedFrames"]) for row in rows),
        "elapsedSeconds": time.monotonic() - started,
    }])
    print("PASS_BCH_S2_06_SMOKE")


def run_burst_smoke(args: argparse.Namespace, repo: Path) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_07_burst_sensitivity"
    paths: list[Path] = []
    lengths = [1, 2, 6, 10, 14, 15, 16, 32, 64]
    for case in CASES:
        for mode in ("PURE", "AWGN"):
            ebn0 = 0.0 if mode == "PURE" else 8.0
            for length in lengths:
                for start in STARTS_BURST:
                    tag = (f"smoke/{case_slug(case)}_{mode.lower()}_"
                           f"l{length}_{start.lower()}")
                    paths.append(execute_point(
                        args, repo, "s2_07", "BURST", case, ebn0, 500, tag,
                        ["--burst-mode", mode, "--burst-length", str(length),
                         "--burst-start-policy", start],
                    ))
    aggregate(stage, "smoke_summary.csv", paths)
    print("PASS_BCH_S2_07_SMOKE")


def run_cfo_formal(args: argparse.Namespace, repo: Path, awgn: list[dict[str, str]]) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_05_residual_cfo"
    phase_paths: list[Path] = []
    rotations = [0, 5, 10, 15, 20, 30, 45, 60, 75, 90, 120, 180]
    for case in CASES:
        refs = awgn_references(awgn, case)
        for snr_index, ebn0 in enumerate(refs):
            for rotation in rotations:
                for phase in PHASES:
                    tag = (f"formal_phase/{case_slug(case)}_s{snr_index}_"
                           f"r{rotation}_p{int(phase)}")
                    phase_paths.append(execute_point(
                        args, repo, "s2_05", "RESIDUAL_CFO", case, ebn0,
                        5000, tag, ["--initial-phase-deg", str(phase),
                                    "--frame-rotation-deg", str(rotation)],
                    ))
    phase_rows = aggregate(stage, "cfo_formal_phase_summary.csv", phase_paths)
    snr_paths: list[Path] = []
    for case in CASES:
        refs = awgn_references(awgn, case)
        for rotation in (30, 60):
            for ebn0 in grid(min(refs[:2]) - 1.0, max(refs[:2]) + 1.0):
                for phase in PHASES:
                    tag = (f"formal_snr/{case_slug(case)}_r{rotation}_"
                           f"e{ebn0:.1f}_p{int(phase)}")
                    snr_paths.append(execute_point(
                        args, repo, "s2_05", "RESIDUAL_CFO", case, ebn0,
                        50000, tag, ["--initial-phase-deg", str(phase),
                                     "--frame-rotation-deg", str(rotation)],
                        adaptive=True,
                    ))
    snr_rows = aggregate(stage, "cfo_formal_snr_summary.csv", snr_paths)
    aggregate_raw(stage, "cfo_phase_aggregate_summary.csv", phase_rows,
                  ["caseName", "sourcePayloadEbN0Db", "frameRotationDeg"])
    aggregate_raw(stage, "cfo_snr_aggregate_summary.csv", snr_rows,
                  ["caseName", "sourcePayloadEbN0Db", "frameRotationDeg"])
    write_rows(stage / "formal_summary.csv", phase_rows + snr_rows)
    make_tolerance(stage, phase_rows, "frameRotationDeg", "cfo_tolerance_summary.csv")
    timing_summary(stage, phase_rows + snr_rows, "cfo_timing_summary.csv")
    print("PASS_BCH_S2_05_RESIDUAL_CFO")


def aggregate_raw(
    stage: Path, filename: str, rows: list[dict[str, str]], fields: list[str],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in fields), []).append(row)
    output: list[dict[str, object]] = []
    for key, values in groups.items():
        frames = sum(int(row["processedFrames"]) for row in values)
        payload_bits = sum(int(row["processedPayloadBits"]) for row in values)
        errors = sum(int(row["decodedFrameErrors"]) for row in values)
        bit_errors = sum(int(row["decodedBitErrors"]) for row in values)
        true_success = sum(int(row["trueSuccessFrames"]) for row in values)
        reported_success = sum(int(row["reportedSuccessFrames"]) for row in values)
        miscorrections = sum(int(row["miscorrectedFrames"]) for row in values)
        failures = sum(int(row["decoderFailureFrames"]) for row in values)
        record = dict(zip(fields, key))
        record.update({
            "payloadLength": values[0]["payloadLength"],
            "encodedLength": values[0]["encodedLength"],
            "frameRate": values[0]["frameRate"],
            "snrDb": values[0]["snrDb"],
            "processedFrames": frames,
            "processedPayloadBits": payload_bits,
            "decodedBitErrors": bit_errors,
            "decodedFrameErrors": errors,
            "BER": bit_errors / payload_bits,
            "FER": errors / frames,
            "trueSuccessFrames": true_success,
            "trueSuccessRate": true_success / frames,
            "reportedSuccessFrames": reported_success,
            "reportedSuccessRate": reported_success / frames,
            "miscorrectedFrames": miscorrections,
            "miscorrectionRate": miscorrections / frames,
            "decoderFailureFrames": failures,
            "decoderFailureRate": failures / frames,
            "channelHardBER": sum(
                float(row["channelHardBER"]) * int(row["processedFrames"])
                for row in values) / frames,
            "avgDecodeTimeUs": sum(
                float(row["avgDecodeTimeUs"]) * int(row["processedFrames"])
                for row in values) / frames,
            "avgTotalReceiverTimeUs": sum(
                float(row["avgTotalReceiverTimeUs"]) * int(row["processedFrames"])
                for row in values) / frames,
            "aggregation": "RAW_COUNTS",
        })
        output.append(record)
    write_rows(stage / filename, output)
    return output


def make_tolerance(
    stage: Path, rows: list[dict[str, str]], parameter: str, filename: str,
) -> None:
    aggregated: dict[tuple[str, float], list[dict[str, str]]] = {}
    for row in rows:
        aggregated.setdefault(
            (row["caseName"], float(row["sourcePayloadEbN0Db"])), []).append(row)
    output: list[dict[str, object]] = []
    for (case, ebn0), values in aggregated.items():
        for target in (0.1, 0.01, 0.5):
            valid = [float(row[parameter]) for row in values
                     if float(row["FER"]) <= target]
            output.append({
                "caseName": case, "sourcePayloadEbN0Db": ebn0,
                "targetFER": target,
                "maximumToleratedParameter": max(valid) if valid else "",
                "parameter": parameter,
                "status": "VALID" if valid else
                          "TARGET_NOT_BRACKETED_NO_EXTRAPOLATION",
            })
    write_rows(stage / filename, output)


def timing_summary(stage: Path, rows: list[dict[str, str]], filename: str) -> None:
    output: list[dict[str, object]] = []
    for case in CASES:
        selected = [row for row in rows if row["caseName"] == case]
        total = sum(int(row["processedFrames"]) for row in selected)
        output.append({
            "caseName": case,
            "processedFrames": total,
            "weightedAvgDecodeTimeUs": sum(
                float(row["avgDecodeTimeUs"]) * int(row["processedFrames"])
                for row in selected) / total,
            "weightedAvgTotalReceiverTimeUs": sum(
                float(row["avgTotalReceiverTimeUs"]) * int(row["processedFrames"])
                for row in selected) / total,
        })
    write_rows(stage / filename, output)


def run_blockage_formal(
    args: argparse.Namespace, repo: Path, awgn: list[dict[str, str]],
) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_06_short_blockage"
    paths: list[Path] = []
    lengths = [1, 2, 4, 6, 8, 10, 12, 14, 15, 16, 20, 24, 29, 30, 31, 32, 48, 64]
    attenuations = [(0, False), (-6, False), (-12, False), (-20, False), (0, True)]
    for case in CASES:
        for snr_index, ebn0 in enumerate(awgn_references(awgn, case)[::2]):
            for attenuation, complete in attenuations:
                for length in lengths:
                    for start in STARTS_BLOCKAGE:
                        profile = "complete" if complete else f"m{abs(attenuation)}"
                        tag = (f"formal_parameter/{case_slug(case)}_s{snr_index}_"
                               f"{profile}_l{length}_{start.lower()}")
                        extra = ["--attenuation-db", str(attenuation),
                                 "--blockage-length", str(length),
                                 "--blockage-start-policy", start]
                        if complete:
                            extra.append("--complete-blockage")
                        paths.append(execute_point(
                            args, repo, "s2_06", "SHORT_BLOCKAGE", case,
                            ebn0, 5000, tag, extra,
                        ))
    parameter_rows = aggregate(
        stage, "blockage_formal_parameter_summary.csv", paths)
    snr_paths: list[Path] = []
    for case in CASES:
        refs = awgn_references(awgn, case)
        for profile, attenuation, length in (("M", -12, 16), ("H", -20, 32)):
            for ebn0 in grid(min(refs[:2]) - 1.0, max(refs[:2]) + 1.0):
                tag = f"formal_snr/{case_slug(case)}_{profile}_e{ebn0:.1f}"
                snr_paths.append(execute_point(
                    args, repo, "s2_06", "SHORT_BLOCKAGE", case, ebn0,
                    50000, tag, ["--attenuation-db", str(attenuation),
                                 "--blockage-length", str(length),
                                 "--blockage-start-policy", "UNIFORM_RANDOM"],
                    adaptive=True,
                ))
    snr_rows = aggregate(stage, "blockage_formal_snr_summary.csv", snr_paths)
    write_rows(stage / "formal_summary.csv", parameter_rows + snr_rows)
    position = aggregate_raw(
        stage, "blockage_position_summary.csv", parameter_rows,
        ["caseName", "sourcePayloadEbN0Db", "attenuationDb",
         "completeBlockage", "blockageLength", "blockageStartPolicy"])
    write_rows(stage / "blockage_boundary_sensitivity.csv", [
        row for row in position if row["blockageStartPolicy"] in
        {"ONE_BEFORE_SEGMENT_BOUNDARY", "ON_SEGMENT_BOUNDARY"}
    ])
    make_tolerance(
        stage, parameter_rows, "blockageLength",
        "blockage_tolerance_summary.csv")
    timing_summary(stage, parameter_rows + snr_rows, "blockage_timing_summary.csv")
    print("PASS_BCH_S2_06_SHORT_BLOCKAGE")


def run_burst_formal(
    args: argparse.Namespace, repo: Path, awgn: list[dict[str, str]],
) -> None:
    stage = repo / "Task/BCH/simulation/stages/s2_07_burst_sensitivity"
    lengths = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 15, 16, 20, 24, 29, 30, 31, 32, 48, 64]
    pure_paths: list[Path] = []
    awgn_paths: list[Path] = []
    for case in CASES:
        for length in lengths:
            for start in STARTS_BURST:
                tag = f"formal_pure/{case_slug(case)}_l{length}_{start.lower()}"
                pure_paths.append(execute_point(
                    args, repo, "s2_07", "BURST", case, 0.0, 5000, tag,
                    ["--burst-mode", "PURE", "--burst-length", str(length),
                     "--burst-start-policy", start],
                ))
        for snr_index, ebn0 in enumerate(awgn_references(awgn, case)[1:]):
            for length in lengths:
                for start in STARTS_BURST:
                    tag = (f"formal_awgn/{case_slug(case)}_s{snr_index}_"
                           f"l{length}_{start.lower()}")
                    awgn_paths.append(execute_point(
                        args, repo, "s2_07", "BURST", case, ebn0, 5000, tag,
                        ["--burst-mode", "AWGN", "--burst-length", str(length),
                         "--burst-start-policy", start],
                    ))
    pure_rows = aggregate(stage, "pure_burst_summary.csv", pure_paths)
    awgn_rows = aggregate(stage, "awgn_burst_summary.csv", awgn_paths)
    write_rows(stage / "formal_summary.csv", pure_rows + awgn_rows)
    start_rows = aggregate_raw(
        stage, "burst_start_sensitivity.csv", pure_rows + awgn_rows,
        ["caseName", "burstMode", "sourcePayloadEbN0Db",
         "burstLength", "burstStartPolicy"])
    write_rows(stage / "burst_boundary_sensitivity.csv", [
        row for row in start_rows if row["burstStartPolicy"] in
        {"ONE_BEFORE_SEGMENT_BOUNDARY", "ON_SEGMENT_BOUNDARY"}
    ])
    make_tolerance(
        stage, pure_rows + awgn_rows, "burstLength",
        "burst_tolerance_summary.csv")
    risk_summary(stage, pure_rows + awgn_rows)
    timing_summary(stage, pure_rows + awgn_rows, "burst_timing_summary.csv")
    print("PASS_BCH_S2_07_BURST_SENSITIVITY")


def risk_summary(stage: Path, rows: list[dict[str, str]]) -> None:
    output_misc: list[dict[str, object]] = []
    output_failure: list[dict[str, object]] = []
    for case in CASES:
        selected = [row for row in rows if row["caseName"] == case]
        frames = sum(int(row["processedFrames"]) for row in selected)
        miscorrections = sum(int(row["miscorrectedFrames"]) for row in selected)
        failures = sum(int(row["decoderFailureFrames"]) for row in selected)
        output_misc.append({"caseName": case, "processedFrames": frames,
                            "miscorrectedFrames": miscorrections,
                            "miscorrectionRate": miscorrections / frames})
        output_failure.append({"caseName": case, "processedFrames": frames,
                               "decoderFailureFrames": failures,
                               "decoderFailureRate": failures / frames})
    write_rows(stage / "burst_miscorrection_summary.csv", output_misc)
    write_rows(stage / "burst_decoder_failure_summary.csv", output_failure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--stage", choices=STAGE_NAMES)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--formal-only", action="store_true")
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--matlab-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--progress", dest="progress", action="store_true")
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.set_defaults(progress=True)
    parser.add_argument("--progress-refresh-seconds", type=float, default=2.0)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--global-seed", type=int, default=SEED)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--worker", action="store_true")
    return parser.parse_args()


def main() -> int:
    global CASES
    args = parse_args()
    repo = Path(__file__).resolve().parents[4]
    if args.case:
        CASES = [args.case]
    if not args.worker:
        initialize_stage_records(repo)
    baseline = baseline_audit(repo, write_output=not args.worker)
    if args.audit_only or args.plot_only or args.matlab_only:
        print("Batch2 specialized post-processing is handled by its dedicated script.")
        return 0
    if not args.worker:
        run(["cmake", "--build", "Task/BCH/simulation/build/current",
             "--config", "Release", "-j", "4"], repo)
        run(["ctest", "--test-dir", "Task/BCH/simulation/build/current",
             "-C", "Release", "--output-on-failure",
             "-R", "bch_s2_impairments_unit|bch_s2_mmse_unit|bch12_awgn_unit"], repo)
    selected = args.stage
    stages = [selected] if selected else ["s2_05", "s2_06", "s2_07"]
    if not args.formal_only:
        if "s2_05" in stages:
            run_cfo_smoke(args, repo, baseline["awgn"])
        if "s2_06" in stages:
            run_blockage_smoke(args, repo, baseline["awgn"])
        if "s2_07" in stages:
            run_burst_smoke(args, repo)
    if not args.smoke_only:
        if "s2_05" in stages:
            run_cfo_formal(args, repo, baseline["awgn"])
        if "s2_06" in stages:
            run_blockage_formal(args, repo, baseline["awgn"])
        if "s2_07" in stages:
            run_burst_formal(args, repo, baseline["awgn"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
