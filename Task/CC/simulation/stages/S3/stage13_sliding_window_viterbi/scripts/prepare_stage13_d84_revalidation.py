#!/usr/bin/env python3
"""Prepare same-noise D84 versus final-balanced Stage13 revalidation."""

from __future__ import annotations

import csv
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
STAGE09 = (
    STAGE.parent
    / "stage09_awgn_formal"
    / "results"
    / "stage09_selected_snr_by_fer_level.csv"
)


def main() -> None:
    with (
        RESULTS / "stage13_final_recommendations.csv"
    ).open(encoding="utf-8", newline="") as stream:
        recommendations = list(csv.DictReader(stream))
    balanced = {
        row["rateCase"]: row
        for row in recommendations
        if row["recommendationType"] == "balanced"
    }
    with STAGE09.open(encoding="utf-8", newline="") as stream:
        selected = list(csv.DictReader(stream))
    rows = []
    for source in selected:
        rate = source["rateCase"]
        level = f"FER_{int(round(float(source['targetFer']) * 100)):03d}"
        common = {
            "runLayer": "d84_revalidation",
            "experimentId": "D84_TRUE_WINDOW_REVALIDATION",
            "rateCase": rate,
            "targetFerLevel": level,
            "snrDb": source["selectedSnrDb"],
            "minFrames": 1000,
            "targetFrameErrors": 200,
            "maxFrames": 50000,
            "sourceStage09RowId": source["sourceRowId"],
        }
        rows.append(
            {
                **common,
                "candidateId": f"{rate}-TRUE-D84",
                "windowBits": 128,
                "slideBits": 25,
                "dtb": 84,
            }
        )
        choice = balanced[rate]
        rows.append(
            {
                **common,
                "candidateId": f"{rate}-FINAL-BALANCED",
                "windowBits": choice["windowBits"],
                "slideBits": choice["slideBits"],
                "dtb": choice["dtb"],
            }
        )
    fields = [
        "runLayer",
        "experimentId",
        "candidateId",
        "rateCase",
        "targetFerLevel",
        "snrDb",
        "windowBits",
        "slideBits",
        "dtb",
        "minFrames",
        "targetFrameErrors",
        "maxFrames",
        "sourceStage09RowId",
    ]
    path = RESULTS / "stage13_d84_revalidation_plan.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"PASS_STAGE13_D84_PLAN rows={len(rows)}")


if __name__ == "__main__":
    main()
