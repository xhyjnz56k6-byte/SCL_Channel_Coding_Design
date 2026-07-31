#!/usr/bin/env python3
"""Substantive final-delivery checker for CC S3 Stage15."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


STAGE = Path(__file__).resolve().parents[1]
S3 = STAGE.parent
RESULTS = STAGE / "results"
RATES = {"R12", "R23", "R34"}
ORGANIZATIONS = {
    "A_BLOCK_300",
    "B_CONT_50x6",
    "C_CONT_100x3",
    "D_CONT_150x2",
}
PLOTS = {
    "stage15_block_soft_ber_by_rate": 30,
    "stage15_block_soft_fer_by_rate": 30,
    "stage15_block_hard_soft_fer": 60,
    "stage15_slot_soft_fer": 372,
    "stage15_slot_hard_fer": 372,
    "stage15_slot_soft_goodput": 372,
    "stage15_slot_first_output_latency": 24,
    "stage15_slot_avg_p95_latency": 12,
    "stage15_quantization_snr_loss": 18,
    "stage15_traceback_memory_reliability": 18,
    "stage15_sliding_parameter_summary": 30,
    "stage15_latency_reliability_pareto": 9,
}


def check_markdown_images(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for relative in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        target = (path.parent / relative).resolve()
        if not target.is_file():
            raise RuntimeError(
                f"invalid Markdown image path in {path.name}: {relative}"
            )


def main() -> None:
    processor = (STAGE / "scripts" / "process_final_delivery.py").read_text(
        encoding="utf-8"
    )
    if "clip(lower=1e-8)" in processor or "observed = group[group[metric] > 0.0]" not in processor:
        raise RuntimeError("log-scale error-floor clipping is forbidden")
    stage14_path = (
        S3
        / "stage14_block_continuous_comparison"
        / "results"
        / "stage14_online_slot_formal_results_all_decisions.csv"
    )
    stage14 = pd.read_csv(stage14_path)
    if len(stage14) != 744:
        raise RuntimeError("Stage14 unified table is not 744 rows")
    if stage14.groupby("decisionMode").size().to_dict() != {
        "Hard": 372,
        "Soft Float": 372,
    }:
        raise RuntimeError("Stage14 Hard/Soft row counts failed")
    if set(stage14.rateCase) != RATES:
        raise RuntimeError("Stage14 rate coverage failed")
    if set(stage14.organization) != ORGANIZATIONS:
        raise RuntimeError("Stage14 organization coverage failed")
    expected_snr = np.arange(-5.0, 10.01, 0.5)
    for key, group in stage14.groupby(
        ["decisionMode", "rateCase", "organization"]
    ):
        if len(group) != 31 or not np.allclose(
            sorted(group.snrDb), expected_snr
        ):
            raise RuntimeError(f"Stage14 SNR grid failed: {key}")
    if not (stage14.frames >= 1000).all():
        raise RuntimeError("Stage14 minimum frames failed")
    if not np.allclose(
        stage14.BER,
        stage14.bitErrors / (stage14.frames * 300),
    ):
        raise RuntimeError("Stage14 BER arithmetic failed")
    if not np.allclose(
        stage14.FER, stage14.frameErrors / stage14.frames
    ):
        raise RuntimeError("Stage14 FER arithmetic failed")
    if not np.allclose(
        stage14.normalizedGoodput,
        stage14.actualRate * (1 - stage14.FER),
    ):
        raise RuntimeError("Stage14 goodput arithmetic failed")

    matrix = pd.read_csv(RESULTS / "stage15_final_scheme_matrix.csv")
    if set(matrix.rate) != RATES:
        raise RuntimeError("Stage15 matrix rate coverage failed")
    matrix14 = matrix[matrix.sourceStage == "Stage14"]
    if len(matrix14) != 744:
        raise RuntimeError(f"Stage14 matrix rows={len(matrix14)}")
    if set(matrix14.organization) != ORGANIZATIONS:
        raise RuntimeError("100x3 or 150x2 missing from Stage15 matrix")
    if set(matrix14.decisionMode) != {"Hard", "Soft Float"}:
        raise RuntimeError("Stage14 Hard missing from Stage15 matrix")
    stage10 = matrix[
        (matrix.sourceStage == "Stage10")
        & (matrix.tracebackMode == "CONTINUOUS_TRUNCATED_VITERBI")
    ]
    if set(stage10.dtb.astype(int)) != {35, 49, 70, 84, 98, 112}:
        raise RuntimeError("Stage10 D coverage failed in matrix")

    for stem, minimum in PLOTS.items():
        image = RESULTS / f"{stem}.png"
        source = RESULTS / "figure_data" / f"{stem}.csv"
        if not image.is_file() or image.stat().st_size < 1000:
            raise RuntimeError(f"missing/empty plot: {image.name}")
        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(f"missing figure data: {source.name}")
        rows = pd.read_csv(source)
        if len(rows) < minimum:
            raise RuntimeError(
                f"figure data too small: {source.name}={len(rows)}<{minimum}"
            )
    trace = pd.read_csv(
        RESULTS
        / "figure_data"
        / "stage15_traceback_memory_reliability.csv"
    )
    if len(trace) != 18:
        raise RuntimeError("traceback memory-reliability must have 18 points")
    if set(trace.dtb.astype(int)) != {35, 49, 70, 84, 98, 112}:
        raise RuntimeError("traceback figure D labels failed")

    recommendations = pd.read_csv(
        RESULTS / "stage15_final_recommendations.csv"
    )
    if set(recommendations.recommendationType) != {
        "reliability_first",
        "throughput_first",
        "latency_first",
        "memory_first",
        "balanced",
    }:
        raise RuntimeError("five recommendation types are incomplete")
    if not recommendations.coveredByData.astype(bool).all():
        raise RuntimeError("a recommendation is not covered by real data")
    if not set(recommendations.comparisonBasis).issubset(
        {"fixed_target_fer", "fixed_snr"}
    ):
        raise RuntimeError("unfair recommendation comparison basis")
    target = recommendations[
        recommendations.comparisonBasis == "fixed_target_fer"
    ]
    fixed = recommendations[
        recommendations.comparisonBasis == "fixed_snr"
    ]
    if not np.allclose(target.targetFer, 0.1):
        raise RuntimeError("fixed-target-FER recommendation mismatch")
    if not np.allclose(fixed.fixedSnrDb, 2.0):
        raise RuntimeError("fixed-SNR recommendation mismatch")

    for path in [
        S3 / "stage14_block_continuous_comparison" / "results"
        / "results_analysis.md",
        RESULTS / "results_analysis.md",
        RESULTS / "cc_s3_final_formal_report.md",
    ]:
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"missing/incomplete report: {path}")
        check_markdown_images(path)
    print(
        "PASS_CC_S3_FINAL_DELIVERY_CHECKER "
        f"stage14=744 matrix={len(matrix)} plots={len(PLOTS)} "
        "tracebackPoints=18 recommendations=5"
    )


if __name__ == "__main__":
    main()
