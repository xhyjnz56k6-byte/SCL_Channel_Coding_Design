#!/usr/bin/env python3
"""Formal Stage10 result checker."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def main() -> None:
    results = Path(__file__).resolve().parents[1] / "results"
    data = pd.read_csv(results / "stage10_traceback_study_results.csv")
    if len(data) != 63:
        raise RuntimeError(f"expected 63 formal rows, found {len(data)}")
    if set(data.rateCase) != {"R12", "R23", "R34"}:
        raise RuntimeError("three-rate coverage failed")
    if set(data.targetFerLevel) != {"FER_030", "FER_010", "FER_003"}:
        raise RuntimeError("three FER-level coverage failed")
    if set(data.dtb) != {35, 49, 70, 84, 98, 112, 306}:
        raise RuntimeError("traceback-depth coverage failed")
    for _, row in data.iterrows():
        if row.frames < 1000 or row.frames > 50000:
            raise RuntimeError("formal frame bound failed")
        if not math.isclose(row.BER, row.bitErrors / (300 * row.frames)):
            raise RuntimeError("BER formula failed")
        if not math.isclose(row.FER, row.frameErrors / row.frames):
            raise RuntimeError("FER formula failed")
        if not row.berCiLow <= row.BER <= row.berCiHigh:
            raise RuntimeError("BER CI failed")
        if not row.ferCiLow <= row.FER <= row.ferCiHigh:
            raise RuntimeError("FER CI failed")
        if not math.isclose(row.esN0Db, row.snrDb, abs_tol=1e-12):
            raise RuntimeError("Es/N0 formula failed")
        expected = row.snrDb - 10 * math.log10(row.actualRate)
        if not math.isclose(row.ebN0Db, expected, abs_tol=1e-12):
            raise RuntimeError("Eb/N0 formula failed")
    for name in [
        "stage10_traceback_ber.png",
        "stage10_traceback_fer.png",
        "stage10_traceback_cpu_latency.png",
        "stage10_traceback_memory.png",
        "stage10_traceback_relative_fer_loss.png",
        "stage10_memory_reliability_tradeoff.png",
        "stage10_d84_window_revalidation.csv",
        "stage10_d84_window_revalidation.md",
    ]:
        if not (results / name).is_file():
            raise RuntimeError(f"missing Stage10 artifact: {name}")
    print("PASS_STAGE10_FORMAL_CHECKER rows=63")


if __name__ == "__main__":
    main()
