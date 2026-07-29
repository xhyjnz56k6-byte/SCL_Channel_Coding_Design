#!/usr/bin/env python3
"""Final CC S3 integration checker."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


REQUIRED_FIELDS = {
    "schemeId",
    "rate",
    "decisionMode",
    "quantMode",
    "quantBits",
    "clipMax",
    "tracebackMode",
    "dtb",
    "window",
    "slide",
    "organization",
    "snrDb",
    "frames",
    "BER",
    "FER",
    "berCiLow",
    "berCiHigh",
    "ferCiLow",
    "ferCiHigh",
    "normalizedGoodput",
    "firstOutputDelaySymbols",
    "avgDecisionDelaySymbols",
    "p95DecisionDelaySymbols",
    "fullFrameLastDecisionSymbol",
    "avgDecodeTimeUs",
    "p95DecodeTimeUs",
    "inputMemoryBytes",
    "survivorMemoryBytes",
    "pathMetricMemoryBytes",
    "totalMemoryBytes",
    "ACSCount",
    "tracebackOperations",
    "sourceStage",
    "sourceCsv",
    "sourceRowId",
    "sourceHash",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    stage = Path(__file__).resolve().parents[1]
    results = stage / "results"
    matrix = pd.read_csv(results / "stage15_final_scheme_matrix.csv")
    if not REQUIRED_FIELDS.issubset(matrix.columns):
        raise RuntimeError("Stage15 matrix schema is incomplete")
    if set(matrix.rate) != {"R12", "R23", "R34"}:
        raise RuntimeError("Stage15 rate coverage failed")
    if not {"Hard", "Soft Float", "Soft Quantized"}.issubset(
        set(matrix.decisionMode)
    ):
        raise RuntimeError("Stage15 decision-mode coverage failed")
    for source, rows in matrix.groupby("sourceCsv"):
        path = stage.parent / source
        if not path.is_file():
            raise RuntimeError(f"missing source CSV: {source}")
        if set(rows.sourceHash) != {sha256(path)}:
            raise RuntimeError(f"source hash mismatch: {source}")
    required_plots = [
        "stage15_final_ber.png",
        "stage15_final_fer.png",
        "stage15_quantization_snr_loss.png",
        "stage15_traceback_memory_reliability.png",
        "stage15_first_output_latency.png",
        "stage15_cpu_decode_latency.png",
        "stage15_goodput_fer_pareto.png",
        "stage15_latency_reliability_pareto.png",
    ]
    for name in required_plots:
        if not (results / name).is_file():
            raise RuntimeError(f"missing final plot: {name}")
    recommendations = pd.read_csv(
        results / "stage15_final_recommendations.csv"
    )
    if set(recommendations.recommendationType) != {
        "reliability_first",
        "throughput_first",
        "latency_first",
        "memory_first",
        "complexity_first",
        "balanced",
    }:
        raise RuntimeError("final recommendation coverage failed")
    for name in [
        "stage15_core_questions_answer.md",
        "stage15_all_figures_guide.md",
        "plot_manifest.json",
        "plot_check.md",
    ]:
        if not (results / name).is_file():
            raise RuntimeError(f"missing final document: {name}")
    print(f"PASS_CC_S3_INTEGRATION rows={len(matrix)} plots=8")


if __name__ == "__main__":
    main()
