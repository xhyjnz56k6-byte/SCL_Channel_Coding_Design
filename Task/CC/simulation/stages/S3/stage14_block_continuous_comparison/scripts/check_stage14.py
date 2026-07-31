#!/usr/bin/env python3
"""Substantive checker for the final Stage14 Hard/Soft delivery."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
RATES = {"R12", "R23", "R34"}
ORGANIZATIONS = {
    "A_BLOCK_300",
    "B_CONT_50x6",
    "C_CONT_100x3",
    "D_CONT_150x2",
}


def main() -> None:
    path = RESULTS / "stage14_online_slot_formal_results_all_decisions.csv"
    data = pd.read_csv(path)
    if len(data) != 744:
        raise RuntimeError(f"unified Stage14 rows={len(data)}, expected 744")
    counts = data.groupby("decisionMode").size().to_dict()
    if counts != {"Hard": 372, "Soft Float": 372}:
        raise RuntimeError(f"decision counts failed: {counts}")
    if set(data.rateCase) != RATES:
        raise RuntimeError("three-rate coverage failed")
    if set(data.organization) != ORGANIZATIONS:
        raise RuntimeError("four-organization coverage failed")
    expected_snr = np.arange(-5.0, 10.01, 0.5)
    groups = data.groupby(["decisionMode", "rateCase", "organization"])
    if len(groups) != 24:
        raise RuntimeError("Hard/Soft x rate x organization coverage failed")
    for key, group in groups:
        if len(group) != 31 or not np.allclose(
            sorted(group.snrDb), expected_snr
        ):
            raise RuntimeError(f"incomplete SNR grid: {key}")
    if not (data.frames >= 1000).all():
        raise RuntimeError("formal minimum-frame condition failed")
    target = data.stopReason == "TARGET_FRAME_ERRORS_REACHED"
    maximum = data.stopReason == "MAX_FRAMES_REACHED"
    if not (
        (target & (data.frameErrors >= 200))
        | (maximum & (data.frames == 50000))
    ).all():
        raise RuntimeError("formal stopping-rule evidence failed")
    if not np.allclose(data.BER, data.bitErrors / (data.frames * 300)):
        raise RuntimeError("BER arithmetic failed")
    if not np.allclose(data.FER, data.frameErrors / data.frames):
        raise RuntimeError("FER arithmetic failed")
    if not np.allclose(
        data.normalizedGoodput, data.actualRate * (1.0 - data.FER)
    ):
        raise RuntimeError("normalized-goodput arithmetic failed")
    block = data[data.organization == "A_BLOCK_300"]
    continuous = data[data.organization != "A_BLOCK_300"]
    if set(block.boundaryStatus) != {"NOT_APPLICABLE"}:
        raise RuntimeError("Block300 boundary status failed")
    if set(continuous.boundaryStatus) != {"APPLICABLE"}:
        raise RuntimeError("continuous boundary status failed")
    if not (
        (continuous.outputBatchCount > 0)
        & (continuous.slotTriggerCount > 0)
        & (continuous.windowTriggerCount > 0)
        & (continuous.peakRxBufferSymbols > 0)
    ).all():
        raise RuntimeError("online slot/window evidence failed")
    if not {"windowBits", "slideBits", "dtb"}.issubset(data.columns):
        raise RuntimeError("W/S/D fields missing")

    required = []
    for token in ("soft", "hard"):
        for rate in ("r12", "r23", "r34"):
            required += [
                f"stage14_{rate}_{token}_ber_by_organization",
                f"stage14_{rate}_{token}_fer_by_organization",
            ]
        required += [
            f"stage14_{token}_goodput_by_rate_and_organization",
            f"stage14_{token}_first_output_latency",
            f"stage14_{token}_avg_p95_decision_latency",
            f"stage14_{token}_buffer_compute_tradeoff",
        ]
    required += [
        f"stage14_{rate}_continuous_output_progress"
        for rate in ("r12", "r23", "r34")
    ]
    required += [
        f"stage14_{rate}_boundary_relative_ber"
        for rate in ("r12", "r23", "r34")
    ]
    for stem in required:
        image = RESULTS / f"{stem}.png"
        source = RESULTS / "figure_data" / f"{stem}.csv"
        if not image.is_file() or image.stat().st_size < 1000:
            raise RuntimeError(f"missing/empty plot: {image.name}")
        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(f"missing figure data: {source.name}")
        if pd.read_csv(source).empty:
            raise RuntimeError(f"empty figure data rows: {source.name}")
    print(
        "PASS_STAGE14_FINAL_CHECKER "
        f"hard={counts['Hard']} soft={counts['Soft Float']} "
        f"all={len(data)} plots={len(required)}"
    )


if __name__ == "__main__":
    main()
