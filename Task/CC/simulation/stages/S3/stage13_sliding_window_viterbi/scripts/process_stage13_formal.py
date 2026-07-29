#!/usr/bin/env python3
"""Merge Stage13 formal shards and select final coarse/dense candidates."""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
RUNTIME = STAGE / "runtime" / "revision_20260729_formal_coarse"
PLAN = RESULTS / "stage13_formal_coarse_plan.csv"
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


def interpolate(points: list[tuple[float, float]], target: float) -> float | None:
    ordered = sorted(points)
    for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
        if y0 >= target >= y1 and y0 > 0 and y1 > 0 and y0 != y1:
            return x0 + (math.log10(target) - math.log10(y0)) * (x1 - x0) / (
                math.log10(y1) - math.log10(y0)
            )
    return None


def interpolation_record(
    points: list[tuple[float, float]], target: float
) -> dict[str, object]:
    ordered = sorted(points)
    for (x0, y0), (x1, y1) in zip(ordered, ordered[1:]):
        if y0 >= target >= y1 and y0 > 0 and y1 > 0 and y0 != y1:
            interpolated = x0 + (
                math.log10(target) - math.log10(y0)
            ) * (x1 - x0) / (math.log10(y1) - math.log10(y0))
            return {
                "leftSnr": x0,
                "leftFer": y0,
                "rightSnr": x1,
                "rightFer": y1,
                "interpolatedSnr": interpolated,
                "interpolationMethod": "linear_in_log10_FER",
                "coveredByData": "YES",
            }
    return {
        "leftSnr": "N/A",
        "leftFer": "N/A",
        "rightSnr": "N/A",
        "rightFer": "N/A",
        "interpolatedSnr": "N/A",
        "interpolationMethod": "N/A",
        "coveredByData": "NO",
    }


def norm(rows: list[dict[str, object]], key: str, row: dict[str, object]) -> float:
    values = [float(item[key]) for item in rows]
    low, high = min(values), max(values)
    return 0.0 if low == high else (float(row[key]) - low) / (high - low)


def main() -> int:
    rows = []
    for index in range(4):
        rows.extend(read_csv(RUNTIME / f"stage13_result_shard_{index}.csv"))
    plan = read_csv(PLAN)
    if len(rows) != len(plan) or len(rows) != 341:
        raise RuntimeError(f"formal row mismatch: {len(rows)} vs {len(plan)}")
    expected = {
        (
            row["rateCase"],
            round(float(row["snrDb"]), 10),
            row["candidateId"],
        )
        for row in plan
    }
    observed = {
        (
            row["rateCase"],
            round(float(row["snrDb"]), 10),
            row["candidateId"],
        )
        for row in rows
    }
    if observed != expected:
        raise RuntimeError("formal plan/result key mismatch")
    output_path = RESULTS / "stage13_formal_coarse_results.csv"
    write_csv(output_path, rows)

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["rateCase"], row["candidateId"])].append(row)
    summaries = []
    snr_loss_rows = []
    for (rate, candidate), points in grouped.items():
        candidate_curve = [
            (float(row["snrDb"]), float(row["FER"])) for row in points
        ]
        block_curve = []
        for row in points:
            fer = float(row["FER"])
            relative = float(row["relativeFerIncreaseVsBlock"])
            block_fer = 0.0 if fer == 0.0 else fer / (1.0 + relative)
            block_curve.append((float(row["snrDb"]), block_fer))
        losses = {}
        for target in (0.1, 0.01):
            candidate_record = interpolation_record(candidate_curve, target)
            block_record = interpolation_record(block_curve, target)
            candidate_snr = (
                None
                if candidate_record["coveredByData"] == "NO"
                else float(candidate_record["interpolatedSnr"])
            )
            block_snr = (
                None
                if block_record["coveredByData"] == "NO"
                else float(block_record["interpolatedSnr"])
            )
            losses[target] = (
                None
                if candidate_snr is None or block_snr is None
                else candidate_snr - block_snr
            )
            snr_loss_rows.append(
                {
                    "rateCase": rate,
                    "candidateId": candidate,
                    "targetFer": target,
                    **candidate_record,
                    "blockLeftSnr": block_record["leftSnr"],
                    "blockLeftFer": block_record["leftFer"],
                    "blockRightSnr": block_record["rightSnr"],
                    "blockRightFer": block_record["rightFer"],
                    "blockInterpolatedSnr": block_record[
                        "interpolatedSnr"
                    ],
                    "blockCoveredByData": block_record["coveredByData"],
                    "snrLossVsBlock": (
                        losses[target]
                        if losses[target] is not None
                        else "N/A"
                    ),
                }
            )
        first = points[0]
        summary: dict[str, object] = {
            "rateCase": rate,
            "candidateId": candidate,
            "windowBits": int(first["windowBits"]),
            "slideBits": int(first["slideBits"]),
            "dtb": int(first["dtb"]),
            "snrLossAtFer01": losses[0.1] if losses[0.1] is not None else "N/A",
            "snrLossAtFer001": losses[0.01] if losses[0.01] is not None else "N/A",
            "worstCoveredSnrLoss": max(
                value for value in losses.values() if value is not None
            ),
            "worstRelativeFerIncreaseVsBlock": max(
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
            "meanTracebackPerFrame": sum(
                float(row["tracebackOperations"]) / int(row["frames"])
                for row in points
            )
            / len(points),
            "meanCpuTimeUs": sum(
                float(row["avgWindowProcessingTimeUs"]) for row in points
            )
            / len(points),
            "formalCorrectnessGate": (
                "PASS"
                if all(
                    int(row["lostBits"]) == 0
                    and int(row["duplicateBits"]) == 0
                    and int(row["outputLength"]) == 300
                    and row["finalFlushPass"] == "1"
                    for row in points
                )
                else "FAIL"
            ),
        }
        summary["reliabilityGate"] = (
            "PASS"
            if summary["formalCorrectnessGate"] == "PASS"
            and float(summary["worstRelativeFerIncreaseVsBlock"]) <= 0.05
            and float(summary["worstCoveredSnrLoss"]) <= 0.2
            else "FAIL"
        )
        summaries.append(summary)

    recommendations = []
    dense_plan = []
    for rate in ("R12", "R23", "R34"):
        qualified = [
            row
            for row in summaries
            if row["rateCase"] == rate and row["reliabilityGate"] == "PASS"
        ]
        if not qualified:
            raise RuntimeError(f"no formal qualified Stage13 candidate: {rate}")
        for row in qualified:
            row["balancedScore"] = (
                WEIGHTS["reliability"] * norm(qualified, "worstCoveredSnrLoss", row)
                + WEIGHTS["delay"] * norm(qualified, "meanP95DecisionDelaySymbols", row)
                + WEIGHTS["memory"] * norm(qualified, "totalMemoryBytes", row)
                + WEIGHTS["operations"]
                * (
                    norm(qualified, "meanACSPerFrame", row)
                    + norm(qualified, "meanTracebackPerFrame", row)
                )
                / 2
                + WEIGHTS["cpuTime"] * norm(qualified, "meanCpuTimeUs", row)
            )
        pareto = []
        pareto_keys = [
            "worstCoveredSnrLoss",
            "meanP95DecisionDelaySymbols",
            "totalMemoryBytes",
            "meanTracebackPerFrame",
            "meanCpuTimeUs",
        ]
        for candidate in qualified:
            dominated = any(
                other is not candidate
                and all(float(other[key]) <= float(candidate[key]) for key in pareto_keys)
                and any(float(other[key]) < float(candidate[key]) for key in pareto_keys)
                for other in qualified
            )
            if not dominated:
                pareto.append(candidate["candidateId"])
        for row in qualified:
            row["paretoFront"] = int(row["candidateId"] in pareto)
        choices = {
            "performance_first": min(
                qualified, key=lambda row: row["worstCoveredSnrLoss"]
            ),
            "latency_first": min(
                qualified, key=lambda row: row["meanP95DecisionDelaySymbols"]
            ),
            "memory_first": min(
                qualified, key=lambda row: row["totalMemoryBytes"]
            ),
            "complexity_first": min(
                qualified,
                key=lambda row: row["meanACSPerFrame"] + row["meanTracebackPerFrame"],
            ),
            "balanced": min(qualified, key=lambda row: row["balancedScore"]),
        }
        for kind, row in choices.items():
            recommendations.append(
                {
                    "rateCase": rate,
                    "recommendationType": kind,
                    **row,
                    "balancedWeights": json.dumps(WEIGHTS, sort_keys=True),
                }
            )
        selected = []
        for kind in ("performance_first", "balanced"):
            identifier = choices[kind]["candidateId"]
            if identifier not in selected:
                selected.append(identifier)
        low, high = {
            "R12": (-2.0, 0.0),
            "R23": (-0.5, 2.0),
            "R34": (0.5, 3.0),
        }[rate]
        for index in range(round((high - low) / 0.1) + 1):
            snr = low + 0.1 * index
            for identifier in selected:
                row = next(item for item in qualified if item["candidateId"] == identifier)
                dense_plan.append(
                    {
                        "runLayer": "formal_dense",
                        "experimentId": "FINAL_DENSE",
                        "candidateId": identifier,
                        "rateCase": rate,
                        "targetFerLevel": "DENSE_GRID",
                        "snrDb": snr,
                        "windowBits": row["windowBits"],
                        "slideBits": row["slideBits"],
                        "dtb": row["dtb"],
                        "minFrames": 1000,
                        "targetFrameErrors": 200,
                        "maxFrames": 50000,
                        "sourceStage09RowId": "STAGE09_DENSE_RANGE",
                    }
                )
    write_csv(RESULTS / "stage13_formal_candidate_summary.csv", summaries)
    write_csv(RESULTS / "stage13_snr_loss.csv", snr_loss_rows)
    write_csv(RESULTS / "stage13_final_recommendations.csv", recommendations)
    write_csv(RESULTS / "stage13_formal_dense_plan.csv", dense_plan)
    print(
        f"PASS_STAGE13_FORMAL_SELECTION coarseRows={len(rows)} "
        f"densePlanRows={len(dense_plan)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
