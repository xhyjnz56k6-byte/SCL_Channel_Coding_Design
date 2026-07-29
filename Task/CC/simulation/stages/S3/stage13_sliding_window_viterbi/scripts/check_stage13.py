#!/usr/bin/env python3
"""Formal Stage13 bounded true-window checker."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    results = Path(__file__).resolve().parents[1] / "results"
    evidence = pd.read_csv(results / "stage13_algorithm_unit_evidence.csv")
    if not (
        (evidence.lostBits == 0)
        & (evidence.duplicateBits == 0)
        & (evidence.outputLength == 300)
        & (evidence.finalFlushPass == 1)
    ).all():
        raise RuntimeError("true-window unit evidence failed")
    coarse = pd.read_csv(results / "stage13_formal_coarse_results.csv")
    dense = pd.read_csv(results / "stage13_formal_dense_results.csv")
    plan = pd.read_csv(results / "stage13_formal_dense_plan.csv")
    reference = pd.read_csv(results / "stage13_reference_comparison.csv")
    comparison = pd.read_csv(results / "stage13_final_comparison.csv")
    if len(coarse) != 341 or len(dense) != len(plan):
        raise RuntimeError("Stage13 formal plan/result coverage failed")
    if len(reference) != 279 or len(comparison) != 558:
        raise RuntimeError("Stage13 reference/final comparison coverage failed")
    if not (
        (coarse.lostBits == 0)
        & (coarse.duplicateBits == 0)
        & (coarse.outputLength == 300)
        & (coarse.finalFlushPass == 1)
    ).all():
        raise RuntimeError("formal output-integrity Gate failed")
    if not (
        coarse.survivorMemoryBytes
        == coarse.windowBits * 64 * 3
    ).all():
        raise RuntimeError("survivor storage is not bounded by W")
    recommendations = pd.read_csv(
        results / "stage13_final_recommendations.csv"
    )
    if len(recommendations) != 15:
        raise RuntimeError("five recommendation classes per rate required")
    if set(recommendations.reliabilityGate) != {"PASS"}:
        raise RuntimeError("unqualified Stage13 recommendation")
    revalidation = pd.read_csv(
        results / "stage10_d84_window_revalidation.csv"
    )
    if len(revalidation) != 45:
        raise RuntimeError("D84 joint revalidation coverage failed")
    if len(list(results.glob("*.png"))) < 15:
        raise RuntimeError("Stage13 research-plot coverage failed")
    print(
        "PASS_STAGE13_FORMAL_CHECKER "
        f"coarse=341 dense={len(dense)} comparison=558"
    )


if __name__ == "__main__":
    main()
