#!/usr/bin/env python3
"""Functional Gate for BCH16W9 timing repair and SNR Chinese figures."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


EXPECTED_FIGURES = {
    "bch_200bit_ber_snr_cn.png": ("200比特BCH误码率对比", "误码率（BER）"),
    "bch_200bit_fer_snr_cn.png": ("200比特BCH误帧率对比", "误帧率（FER）"),
    "bch_200bit_decode_time_snr_cn.png": ("200比特BCH平均译码时延", "平均译码时延（μs）"),
    "bch_300bit_ber_snr_cn.png": ("300比特BCH误码率对比", "误码率（BER）"),
    "bch_300bit_fer_snr_cn.png": ("300比特BCH误帧率对比", "误帧率（FER）"),
    "bch_300bit_decode_time_snr_cn.png": ("300比特BCH平均译码时延", "平均译码时延（μs）"),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--formal-summary", type=Path, required=True)
    parser.add_argument("--timing-result-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()

    adapter_path = (
        args.repo_root / "Task/BCH/simulation/current/src/bch_case_adapter.cpp"
    )
    simulation_path = (
        args.repo_root / "Task/BCH/simulation/current/src/bch_awgn_simulation.cpp"
    )
    adapter = adapter_path.read_text(encoding="utf-8")
    simulation = simulation_path.read_text(encoding="utf-8")

    if "const block::BlockBchProfile& blockProfile(BchCaseId id)" not in adapter:
        raise SystemExit("BLOCKED_BCH16W9_PROFILE_NOT_RETURNED_BY_REFERENCE")
    for maker in ("makeB200Profile()", "makeB300Profile()", "makeB300426Profile()"):
        if adapter.count(maker) != 1:
            raise SystemExit(f"BLOCKED_BCH16W9_PROFILE_FACTORY_COUNT: {maker}")
    if adapter.count("static const block::BlockBchProfile profile") != 3:
        raise SystemExit("BLOCKED_BCH16W9_PROFILE_CACHE_COUNT")
    if "void prepareBchCase(" not in adapter:
        raise SystemExit("BLOCKED_BCH16W9_PREPARE_API_MISSING")
    prepare_index = simulation.find("prepareBchCase(simulationCase);")
    loop_index = simulation.find("for (std::uint64_t offset = result.processedFrames;")
    if prepare_index < 0 or loop_index < 0 or prepare_index >= loop_index:
        raise SystemExit("BLOCKED_BCH16W9_PREPARE_NOT_BEFORE_TIMED_LOOP")
    if "config.timingWarmupFrames" not in simulation:
        raise SystemExit("BLOCKED_BCH16W9_WARMUP_NOT_IMPLEMENTED")

    formal = rows(args.formal_summary)
    repetitions = rows(args.timing_result_dir / "timing_repetitions.csv")
    timing = rows(args.timing_result_dir / "timing_summary.csv")
    if len(formal) != 74 or len(timing) != 74 or len(repetitions) != 222:
        raise SystemExit(
            "BLOCKED_BCH16W9_TIMING_COUNTS "
            f"formal={len(formal)} timing={len(timing)} repetitions={len(repetitions)}"
        )
    for row in repetitions:
        values = [
            float(row["avgDecodeTimeUs"]),
            float(row["p50DecodeTimeUs"]),
            float(row["p95DecodeTimeUs"]),
            float(row["p99DecodeTimeUs"]),
            float(row["maxDecodeTimeUs"]),
        ]
        if (
            int(row["warmupFrames"]) != 500
            or int(row["timedFrames"]) != 5000
            or any(not math.isfinite(value) or value <= 0.0 for value in values)
        ):
            raise SystemExit("BLOCKED_BCH16W9_INVALID_REPETITION")
    for row in timing:
        if (
            int(row["warmupFrames"]) != 500
            or int(row["timedFramesPerRepetition"]) != 5000
            or int(row["repetitions"]) != 3
            or not math.isfinite(float(row["publishedAvgDecodeTimeUs"]))
            or float(row["publishedAvgDecodeTimeUs"]) <= 0.0
        ):
            raise SystemExit("BLOCKED_BCH16W9_INVALID_PUBLISHED_TIMING")

    figures_dir = args.stage_dir / "figures"
    manifest = json.loads((figures_dir / "plot_manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != 6 or {item["filename"] for item in manifest} != set(EXPECTED_FIGURES):
        raise SystemExit("BLOCKED_BCH16W9_FIGURE_MANIFEST")
    source_by_key = {
        (row["caseName"], row["ebn0Db"]): row for row in formal
    }
    for item in manifest:
        expected_title, expected_y = EXPECTED_FIGURES[item["filename"]]
        if (
            item["title"] != expected_title
            or item["xLabel"] != "SNR（dB）"
            or item["yLabel"] != expected_y
            or item["xColumn"] != "snrDb"
        ):
            raise SystemExit("BLOCKED_BCH16W9_CHINESE_LABEL_MISMATCH")
        image = figures_dir / item["filename"]
        if image.stat().st_size < 1000 or image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("BLOCKED_BCH16W9_INVALID_PNG")
        figure_rows = rows(figures_dir / item["figureDataCsv"])
        metric = item["metric"]
        for row in figure_rows:
            source = source_by_key[(row["caseName"], row["sourceEbN0Db"])]
            expected_snr = float(source["ebn0Db"]) + 10.0 * math.log10(
                float(source["frameRate"])
            )
            if abs(float(row["snrDb"]) - expected_snr) > 1e-12:
                raise SystemExit("BLOCKED_BCH16W9_SNR_FORMULA")
            if metric in {"BER", "FER"} and float(row[metric]) != float(source[metric]):
                raise SystemExit("BLOCKED_BCH16W9_BER_FER_CHANGED")

    correction = {row["caseName"]: row for row in rows(args.stage_dir / "result_summary.csv")}
    for case_name in ("BCH-B200", "BCH-B300", "BCH-B300-426"):
        old_value = float(correction[case_name]["oldWeightedAvgDecodeTimeUs"])
        new_value = float(correction[case_name]["newWeightedAvgDecodeTimeUs"])
        if not (0.0 < new_value < old_value):
            raise SystemExit(f"BLOCKED_BCH16W9_TIMING_NOT_REPAIRED: {case_name}")

    print(
        "PASS_BCH16W9_FUNCTIONAL_GATE "
        "profileCaches=3 timingPoints=74 timingMeasurements=222 figures=6"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
