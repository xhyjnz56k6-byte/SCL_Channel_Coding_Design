#!/usr/bin/env python3
"""Build the strict W/S/D control-variable prescan plan from Stage09."""

from __future__ import annotations

import csv
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
S3 = STAGE.parents[0]
SOURCE = S3 / "stage09_awgn_formal" / "results" / "stage09_selected_snr_by_fer_level.csv"
OUTPUT = STAGE / "results" / "stage13_controlled_prescan_plan.csv"
CONFIGS = [
    ("A_CHANGE_W", 96, 16, 70),
    ("A_CHANGE_W", 128, 16, 70),
    ("A_CHANGE_W", 160, 16, 70),
    ("A_CHANGE_W", 192, 16, 70),
    ("B_CHANGE_S", 128, 8, 70),
    ("B_CHANGE_S", 128, 16, 70),
    ("B_CHANGE_S", 128, 25, 70),
    ("B_CHANGE_S", 128, 50, 70),
    ("C_CHANGE_D", 128, 25, 35),
    ("C_CHANGE_D", 128, 25, 49),
    ("C_CHANGE_D", 128, 25, 70),
    ("C_CHANGE_D", 128, 25, 84),
    ("C_CHANGE_D", 128, 25, 98),
]


def main() -> int:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        selected = list(csv.DictReader(stream))
    rows = []
    for point in selected:
        target = float(point["targetFer"])
        level = (
            "FER_030"
            if target >= 0.2
            else ("FER_010" if target >= 0.05 else "FER_003")
        )
        for experiment, window, slide, depth in CONFIGS:
            if not (window > depth and slide <= window - depth):
                raise RuntimeError("illegal controlled configuration")
            rows.append(
                {
                    "runLayer": "prescan",
                    "experimentId": experiment,
                    "candidateId": f"W{window}-S{slide}-D{depth}",
                    "rateCase": point["rateCase"],
                    "targetFerLevel": level,
                    "snrDb": point["selectedSnrDb"],
                    "windowBits": window,
                    "slideBits": slide,
                    "dtb": depth,
                    "minFrames": 1000,
                    "targetFrameErrors": 200,
                    "maxFrames": 1000,
                    "sourceStage09RowId": point["sourceRowId"],
                }
            )
    if len(rows) != 117:
        raise RuntimeError(f"expected 117 prescan rows, got {len(rows)}")
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"PASS_STAGE13_PRESCAN_PLAN rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
