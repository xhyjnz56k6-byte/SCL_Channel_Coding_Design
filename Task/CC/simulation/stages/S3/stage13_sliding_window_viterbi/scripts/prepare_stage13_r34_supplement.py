#!/usr/bin/env python3
"""Create legal deeper-traceback R34 candidates after the first Gate shortage."""

from __future__ import annotations

import csv
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
S3 = STAGE.parent
SOURCE = S3 / "stage09_awgn_formal" / "results" / "stage09_selected_snr_by_fer_level.csv"
OUTPUT = STAGE / "results" / "stage13_r34_supplement_plan.csv"
CONFIGS = [
    (160, 25, 112),
    (192, 25, 112),
    (160, 16, 112),
    (192, 50, 112),
    (160, 25, 126),
    (192, 25, 126),
]


def main() -> int:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        selected = [
            row for row in csv.DictReader(stream) if row["rateCase"] == "R34"
        ]
    rows = []
    for point in selected:
        target = float(point["targetFer"])
        level = (
            "FER_030"
            if target >= 0.2
            else ("FER_010" if target >= 0.05 else "FER_003")
        )
        for window, slide, depth in CONFIGS:
            if not (window > depth and slide <= window - depth):
                raise RuntimeError("illegal supplemental configuration")
            rows.append(
                {
                    "runLayer": "prescan_supplement",
                    "experimentId": "R34_GATE_SUPPLEMENT",
                    "candidateId": f"W{window}-S{slide}-D{depth}",
                    "rateCase": "R34",
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
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"PASS_STAGE13_R34_SUPPLEMENT_PLAN rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
