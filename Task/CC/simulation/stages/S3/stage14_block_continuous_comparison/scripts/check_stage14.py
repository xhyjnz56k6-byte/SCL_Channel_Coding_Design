#!/usr/bin/env python3
"""Formal Stage14 online-slot checker."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    results = Path(__file__).resolve().parents[1] / "results"
    coarse = pd.read_csv(results / "stage14_online_slot_formal_results.csv")
    dense = pd.read_csv(results / "stage14_online_slot_dense_results.csv")
    offsets = pd.read_csv(results / "stage14_boundary_offset_results.csv")
    if len(coarse) != 372 or len(dense) != 146:
        raise RuntimeError("Stage14 coarse/dense coverage failed")
    if set(coarse.rateCase) != {"R12", "R23", "R34"}:
        raise RuntimeError("three-rate coverage failed")
    if set(coarse.organization) != {
        "A_BLOCK_300",
        "B_CONT_50x6",
        "C_CONT_100x3",
        "D_CONT_150x2",
    }:
        raise RuntimeError("organization coverage failed")
    block = coarse[coarse.organization == "A_BLOCK_300"]
    if set(block.boundaryStatus) != {"NOT_APPLICABLE"}:
        raise RuntimeError("block boundary must be NOT_APPLICABLE")
    continuous = coarse[coarse.organization != "A_BLOCK_300"]
    if set(continuous.boundaryStatus) != {"APPLICABLE"}:
        raise RuntimeError("continuous boundary status failed")
    if set(offsets.relativeOffset) != set(range(-10, 10)):
        raise RuntimeError("boundary offset coverage failed")
    if len(offsets) != 5580:
        raise RuntimeError("boundary formal row count failed")
    if not (
        (continuous.outputBatchCount > 0)
        & (continuous.slotTriggerCount > 0)
        & (continuous.windowTriggerCount > 0)
        & (continuous.peakRxBufferSymbols > 0)
    ).all():
        raise RuntimeError("online scheduler evidence failed")
    if len(list(results.glob("stage14_*.png"))) < 18:
        raise RuntimeError("Stage14 per-rate plot coverage failed")
    print("PASS_STAGE14_FORMAL_CHECKER coarse=372 dense=146 offsets=5580")


if __name__ == "__main__":
    main()
