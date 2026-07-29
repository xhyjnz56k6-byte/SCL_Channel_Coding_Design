#!/usr/bin/env python3
"""Formal Stage11 result checker."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def validate_rows(data: pd.DataFrame, expected: int) -> None:
    if len(data) != expected:
        raise RuntimeError(f"expected {expected} rows, found {len(data)}")
    for _, row in data.iterrows():
        if row.frames < 1000 or row.frames > 50000:
            raise RuntimeError("formal frame bound failed")
        if not math.isclose(row.BER, row.bitErrors / (300 * row.frames)):
            raise RuntimeError("BER formula failed")
        if not math.isclose(row.FER, row.frameErrors / row.frames):
            raise RuntimeError("FER formula failed")
        if row.integerOverflowCount != 0 or row.pathMetricSaturationCount != 0:
            raise RuntimeError("quantized metric overflow/saturation")
        if not math.isclose(row.esN0Db, row.snrDb, abs_tol=1e-12):
            raise RuntimeError("Es/N0 formula failed")


def main() -> None:
    results = Path(__file__).resolve().parents[1] / "results"
    prescan = pd.read_csv(results / "stage11_quantization_prescan.csv")
    coarse = pd.read_csv(results / "stage11_quantization_coarse_results.csv")
    dense = pd.read_csv(results / "stage11_quantization_dense_results.csv")
    if len(prescan) != 30:
        raise RuntimeError("clip prescan coverage failed")
    if set(prescan.quantMode) != {f"Q{bits}" for bits in range(3, 9)}:
        raise RuntimeError("clip prescan quantization coverage failed")
    validate_rows(coarse, 651)
    validate_rows(dense, 365)
    if set(coarse.rateCase) != {"R12", "R23", "R34"}:
        raise RuntimeError("three-rate coverage failed")
    if set(coarse.quantMode) != {
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
        "Q8",
        "Float",
    }:
        raise RuntimeError("formal quantization coverage failed")
    if set(dense.quantMode) != {"Q5", "Q6", "Q7", "Q8", "Float"}:
        raise RuntimeError("dense quantization coverage failed")
    recommendation = pd.read_csv(
        results / "stage11_quantization_recommendation.csv"
    )
    if set(recommendation.balanced) != {"Q8"}:
        raise RuntimeError("balanced recommendation is not data-derived Q8")
    if len(list(results.glob("*.png"))) < 13:
        raise RuntimeError("Stage11 plot coverage failed")
    print("PASS_STAGE11_FORMAL_CHECKER coarse=651 dense=365 balanced=Q8")


if __name__ == "__main__":
    main()
