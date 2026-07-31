#!/usr/bin/env python3
"""Apply hard Gates, Pareto filtering and weighted Stage13 recommendations."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
SOURCE = RESULTS / "stage13_controlled_prescan_results.csv"
SUPPLEMENT = RESULTS / "stage13_r34_supplement_results.csv"
RANGES = {"R12": (-2.0, 0.0), "R23": (-0.5, 2.0), "R34": (0.5, 3.0)}
WEIGHTS = {
    "reliability": 0.35,
    "delay": 0.20,
    "memory": 0.20,
    "operations": 0.15,
    "cpuTime": 0.10,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def dominates(lhs: dict[str, object], rhs: dict[str, object]) -> bool:
    keys = [
        "worstRelativeFerIncrease",
        "meanFirstOutputDelaySymbols",
        "totalMemoryBytes",
        "meanACSPerFrame",
        "meanTracebackOperationsPerFrame",
        "meanCpuTimeUs",
    ]
    return all(float(lhs[key]) <= float(rhs[key]) for key in keys) and any(
        float(lhs[key]) < float(rhs[key]) for key in keys
    )


def normalize(rows: list[dict[str, object]], key: str, row: dict[str, object]) -> float:
    values = [float(item[key]) for item in rows]
    low, high = min(values), max(values)
    return 0.0 if high == low else (float(row[key]) - low) / (high - low)


def main() -> int:
    rows = read_csv(SOURCE) + read_csv(SUPPLEMENT)
    if len(rows) != 135:
        raise RuntimeError(f"expected 135 prescan rows, got {len(rows)}")
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["rateCase"], row["candidateId"])].append(row)
    summaries: list[dict[str, object]] = []
    for (rate, candidate), raw_points in grouped.items():
        points_by_level: dict[str, dict[str, str]] = {}
        for point in raw_points:
            points_by_level.setdefault(point["targetFerLevel"], point)
        points = list(points_by_level.values())
        if len(points) != 3:
            raise RuntimeError(f"prescan coverage mismatch: {rate}/{candidate}")
        first = points[0]
        summary: dict[str, object] = {
            "rateCase": rate,
            "candidateId": candidate,
            "windowBits": int(first["windowBits"]),
            "slideBits": int(first["slideBits"]),
            "dtb": int(first["dtb"]),
            "noiselessMismatch": 0,
            "lostBits": max(int(row["lostBits"]) for row in points),
            "duplicateBits": max(int(row["duplicateBits"]) for row in points),
            "outputLength": min(int(row["outputLength"]) for row in points),
            "finalFlushPass": all(row["finalFlushPass"] == "1" for row in points),
            "worstRelativeFerIncrease": max(
                float(row["relativeFerIncreaseVsBlock"]) for row in points
            ),
            "meanFirstOutputDelaySymbols": sum(
                float(row["firstOutputDelaySymbols"]) for row in points
            )
            / len(points),
            "meanP95DecisionDelaySymbols": sum(
                float(row["p95DecisionDelaySymbols"]) for row in points
            )
            / len(points),
            "totalMemoryBytes": int(first["totalMemoryBytes"]),
            "meanACSPerFrame": sum(
                float(row["ACSCount"]) / int(row["frames"]) for row in points
            )
            / len(points),
            "meanTracebackOperationsPerFrame": sum(
                float(row["tracebackOperations"]) / int(row["frames"])
                for row in points
            )
            / len(points),
            "meanCpuTimeUs": sum(
                float(row["avgWindowProcessingTimeUs"]) for row in points
            )
            / len(points),
        }
        correct = (
            summary["lostBits"] == 0
            and summary["duplicateBits"] == 0
            and summary["outputLength"] == 300
            and summary["finalFlushPass"]
        )
        summary["correctnessGate"] = "PASS" if correct else "FAIL"
        summary["reliabilityGate"] = (
            "PASS"
            if correct and summary["worstRelativeFerIncrease"] <= 0.05
            else "FAIL"
        )
        summaries.append(summary)

    formal_plan = []
    recommendation_rows = []
    for rate in ("R12", "R23", "R34"):
        qualified = [
            row
            for row in summaries
            if row["rateCase"] == rate and row["reliabilityGate"] == "PASS"
        ]
        if len(qualified) < 2:
            raise RuntimeError(f"fewer than two qualified candidates for {rate}")
        for row in qualified:
            row["pareto"] = not any(
                other is not row and dominates(other, row) for other in qualified
            )
            row["balancedScore"] = (
                WEIGHTS["reliability"]
                * normalize(qualified, "worstRelativeFerIncrease", row)
                + WEIGHTS["delay"]
                * normalize(qualified, "meanP95DecisionDelaySymbols", row)
                + WEIGHTS["memory"]
                * normalize(qualified, "totalMemoryBytes", row)
                + WEIGHTS["operations"]
                * (
                    normalize(qualified, "meanACSPerFrame", row)
                    + normalize(
                        qualified, "meanTracebackOperationsPerFrame", row
                    )
                )
                / 2.0
                + WEIGHTS["cpuTime"]
                * normalize(qualified, "meanCpuTimeUs", row)
            )
        choices = {
            "performance_first": min(
                qualified, key=lambda row: row["worstRelativeFerIncrease"]
            ),
            "latency_first": min(
                qualified, key=lambda row: row["meanP95DecisionDelaySymbols"]
            ),
            "memory_first": min(
                qualified, key=lambda row: row["totalMemoryBytes"]
            ),
            "complexity_first": min(
                qualified,
                key=lambda row: (
                    row["meanACSPerFrame"]
                    + row["meanTracebackOperationsPerFrame"]
                ),
            ),
            "balanced": min(qualified, key=lambda row: row["balancedScore"]),
        }
        selected_ids = []
        for row in sorted(
            (item for item in qualified if item["pareto"]),
            key=lambda item: item["balancedScore"],
        ):
            if row["candidateId"] not in selected_ids:
                selected_ids.append(str(row["candidateId"]))
            if len(selected_ids) == 4:
                break
        for kind in ("balanced", "performance_first"):
            identifier = str(choices[kind]["candidateId"])
            if identifier not in selected_ids:
                selected_ids.append(identifier)
        selected_ids = selected_ids[:4]
        if len(selected_ids) < 2:
            selected_ids = [
                str(row["candidateId"])
                for row in sorted(qualified, key=lambda item: item["balancedScore"])[:2]
            ]
        for kind, row in choices.items():
            recommendation_rows.append(
                {
                    "rateCase": rate,
                    "recommendationType": kind,
                    **row,
                    "balancedWeights": json.dumps(
                        WEIGHTS, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
        for snr_index in range(31):
            snr = -5.0 + 0.5 * snr_index
            for identifier in selected_ids:
                row = next(
                    item
                    for item in qualified
                    if item["candidateId"] == identifier
                )
                formal_plan.append(
                    {
                        "runLayer": "formal_coarse",
                        "experimentId": "AUTO_SELECTED",
                        "candidateId": identifier,
                        "rateCase": rate,
                        "targetFerLevel": "GRID",
                        "snrDb": snr,
                        "windowBits": row["windowBits"],
                        "slideBits": row["slideBits"],
                        "dtb": row["dtb"],
                        "minFrames": 1000,
                        "targetFrameErrors": 200,
                        "maxFrames": 50000,
                        "sourceStage09RowId": "COARSE_GRID",
                    }
                )
        for row in summaries:
            if row["rateCase"] == rate:
                row["selectedForFormal"] = (
                    "YES" if row["candidateId"] in selected_ids else "NO"
                )
    write_csv(RESULTS / "stage13_candidate_summary.csv", summaries)
    write_csv(RESULTS / "stage13_recommendations_prescan.csv", recommendation_rows)
    write_csv(RESULTS / "stage13_formal_coarse_plan.csv", formal_plan)
    print(
        f"PASS_STAGE13_AUTO_SELECTION candidates={len(formal_plan) // 31} "
        f"formalRows={len(formal_plan)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
