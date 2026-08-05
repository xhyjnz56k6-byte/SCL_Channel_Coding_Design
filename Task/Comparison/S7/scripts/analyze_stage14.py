import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMAL = {
    "BCH": ROOT / "stage10_bch_formal" / "results" / "formal_results.csv",
    "CC": ROOT / "stage11_cc_formal" / "results" / "formal_results.csv",
}


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def normalized(values, value):
    low, high = min(values), max(values)
    return 0.0 if high == low else (value - low) / (high - low)


def target_crossing(points, target=0.5):
    crossings = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 == target: crossings.append(x0)
        elif (y0 - target) * (y1 - target) < 0 and y0 > 0 and y1 > 0:
            log0, log1, logt = math.log10(y0), math.log10(y1), math.log10(target)
            crossings.append(x0 + (x1 - x0) * (logt - log0) / (log1 - log0))
    if points and points[-1][1] == target: crossings.append(points[-1][0])
    unique = []
    for value in crossings:
        if not unique or abs(value - unique[-1]) > 1e-12: unique.append(value)
    if len(unique) == 1: return unique[0], "INTERPOLATED"
    if not unique: return None, "TARGET_NOT_BRACKETED"
    return None, "NON_MONOTONIC_MULTIPLE_CROSSINGS"


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stage14_fer_improvement" / "results"
    all_rows = {}
    improvement = []
    improvement_fields = ["scheme", "configurationId", "method", "comparisonRole", "engineeringComparisonGroup", "controlledComparisonGroup", "pureMethodDifferenceAllowed", "EsN0Db", "burstRatioRequested", "meanPositionFer", "worstPositionFer", "bestPositionFer", "positionSensitivity", "baselineMeanPositionFer", "absoluteFerImprovement", "relativeFerReductionPercent", "improvementFactor", "relativeMetricStatus", "sourceAbsolutePath"]
    for scheme, source in FORMAL.items():
        rows = list(csv.DictReader(source.open(encoding="utf-8")))
        all_rows[scheme] = rows
        grouped = defaultdict(list)
        for row in rows: grouped[(row["configurationId"], row["EsN0Db"], row["burstRatioRequested"])].append(row)
        baseline = {key[1:]: sum(float(r["FER"]) for r in group) / len(group) for key, group in grouped.items() if group[0]["comparisonRole"] == "BASELINE"}
        for key, group in sorted(grouped.items()):
            config, snr, ratio = key; fers = [float(row["FER"]) for row in group]
            base = baseline[(snr, ratio)]; mean_fer = sum(fers) / len(fers)
            absolute = base - mean_fer
            relative = "" if base == 0 else 100.0 * absolute / base
            factor = "" if mean_fer == 0 else base / mean_fer
            improvement.append({
                "scheme": scheme, "configurationId": config, "method": group[0]["method"],
                "comparisonRole": group[0]["comparisonRole"], "engineeringComparisonGroup": group[0]["engineeringComparisonGroup"],
                "controlledComparisonGroup": group[0]["controlledComparisonGroup"], "pureMethodDifferenceAllowed": "false",
                "EsN0Db": snr, "burstRatioRequested": ratio, "meanPositionFer": mean_fer,
                "worstPositionFer": max(fers), "bestPositionFer": min(fers),
                "positionSensitivity": max(fers) - min(fers), "baselineMeanPositionFer": base,
                "absoluteFerImprovement": absolute, "relativeFerReductionPercent": relative,
                "improvementFactor": factor, "relativeMetricStatus": "BASELINE_ZERO_UNDEFINED" if base == 0 else "DEFINED",
                "sourceAbsolutePath": str(source.resolve())})
    write_csv(out_dir / "fer_improvement_summary.csv", improvement_fields, improvement)

    target_rows = []
    target_fields = ["scheme", "configurationId", "burstRatioRequested", "targetFer", "configurationEsN0Db", "baselineEsN0Db", "esN0GainDb", "configurationStatus", "baselineStatus", "interpolationMethod"]
    for scheme, rows in all_rows.items():
        aggregate = defaultdict(list)
        roles = {}
        for row in rows:
            key = (row["configurationId"], float(row["burstRatioRequested"]), float(row["EsN0Db"]))
            aggregate[key].append(float(row["FER"])); roles[row["configurationId"]] = row["comparisonRole"]
        configs = sorted(roles)
        for ratio in (0.02, 0.05, 0.10):
            crossings = {}
            for config in configs:
                points = sorted((snr, sum(vals) / len(vals)) for (cid, r, snr), vals in aggregate.items() if cid == config and r == ratio)
                crossings[config] = target_crossing(points)
            baseline_id = next(config for config in configs if roles[config] == "BASELINE")
            base_value, base_status = crossings[baseline_id]
            for config in configs:
                value, status = crossings[config]
                gain = base_value - value if value is not None and base_value is not None else ""
                target_rows.append({"scheme": scheme, "configurationId": config, "burstRatioRequested": ratio,
                                    "targetFer": 0.5, "configurationEsN0Db": "" if value is None else value,
                                    "baselineEsN0Db": "" if base_value is None else base_value, "esN0GainDb": gain,
                                    "configurationStatus": status, "baselineStatus": base_status,
                                    "interpolationMethod": "linear_in_log10_FER_without_smoothing"})
    write_csv(out_dir / "target_fer_esn0_gain.csv", target_fields, target_rows)

    tolerance_rows = []
    tolerance_fields = ["scheme", "configurationId", "highEsN0Db", "ferThreshold", "largestTestedBurstRatioMeetingThreshold", "burstToleranceStatus", "worstPositionFerAt2Percent", "worstPositionFerAt5Percent", "worstPositionFerAt10Percent"]
    for scheme, rows in all_rows.items():
        high = max(float(row["EsN0Db"]) for row in rows)
        configs = sorted({row["configurationId"] for row in rows})
        for config in configs:
            worst = {}
            for ratio in (0.02, 0.05, 0.10):
                values = [float(row["FER"]) for row in rows if row["configurationId"] == config and float(row["EsN0Db"]) == high and float(row["burstRatioRequested"]) == ratio]
                worst[ratio] = max(values)
            passing = [ratio for ratio, value in worst.items() if value <= 0.1]
            tolerance_rows.append({"scheme": scheme, "configurationId": config, "highEsN0Db": high,
                                   "ferThreshold": 0.1, "largestTestedBurstRatioMeetingThreshold": max(passing) if passing else "",
                                   "burstToleranceStatus": "WITHIN_TESTED_GRID" if passing else "BELOW_MIN_TESTED_2_PERCENT",
                                   "worstPositionFerAt2Percent": worst[0.02], "worstPositionFerAt5Percent": worst[0.05],
                                   "worstPositionFerAt10Percent": worst[0.10]})
    write_csv(out_dir / "burst_tolerance_summary.csv", tolerance_fields, tolerance_rows)

    latency = list(csv.DictReader((ROOT / "stage13_latency_complexity" / "results" / "latency_complexity_summary.csv").open(encoding="utf-8")))
    start_rows = list(csv.DictReader((ROOT / "stage12_all_start_scan" / "results" / "all_start_summary.csv").open(encoding="utf-8")))
    ranking = []
    ranking_fields = ["scheme", "rank", "configurationId", "method", "interpretationScope", "meanFormalFer", "worstHighWorkpointStartFer", "bufferBits", "deinterleaveTimeMeanNsWeighted", "ferNormalized", "worstStartNormalized", "bufferNormalized", "deinterleaveNormalized", "weightedScore", "paretoOptimal", "weightFer", "weightWorstStart", "weightBuffer", "weightDeinterleave"]
    for scheme in ("BCH", "CC"):
        candidates = [row for row in latency if row["scheme"] == scheme and row["comparisonRole"] != "BASELINE"]
        metrics = []
        for candidate in candidates:
            config = candidate["configurationId"]
            mean_formal = sum(float(row["FER"]) for row in all_rows[scheme] if row["configurationId"] == config) / 558
            high_starts = [float(row["worstFer"]) for row in start_rows if row["scheme"] == scheme and row["configurationId"] == config and row["workpointRole"] == "HIGH"]
            metrics.append({"row": candidate, "fer": mean_formal, "worst": max(high_starts), "buffer": float(candidate["bufferBits"]), "deint": float(candidate["deinterleaveTimeMeanNsWeighted"])})
        arrays = {field: [item[field] for item in metrics] for field in ("fer", "worst", "buffer", "deint")}
        for item in metrics:
            item.update({field + "Norm": normalized(arrays[field], item[field]) for field in arrays})
            item["score"] = 0.40 * item["ferNorm"] + 0.30 * item["worstNorm"] + 0.15 * item["bufferNorm"] + 0.15 * item["deintNorm"]
            item["pareto"] = not any(all(other[field] <= item[field] for field in arrays) and any(other[field] < item[field] for field in arrays) for other in metrics)
        for rank, item in enumerate(sorted(metrics, key=lambda value: (value["score"], value["row"]["configurationId"])), 1):
            row = item["row"]
            if scheme == "CC":
                scopes = []
                if row["engineeringComparisonGroup"]: scopes.append("RECOMMENDED_ENGINEERING_CONFIGURATION_COMPARISON")
                if row["controlledComparisonGroup"]: scopes.append("CONTROLLED_EQUAL_SPAN_128_COMPARISON")
                scope = ";".join(scopes)
            else: scope = "CONTROLLED_EQUAL_SPAN_285_COMPARISON"
            ranking.append({"scheme": scheme, "rank": rank, "configurationId": row["configurationId"], "method": row["method"], "interpretationScope": scope,
                            "meanFormalFer": item["fer"], "worstHighWorkpointStartFer": item["worst"], "bufferBits": item["buffer"],
                            "deinterleaveTimeMeanNsWeighted": item["deint"], "ferNormalized": item["ferNorm"], "worstStartNormalized": item["worstNorm"],
                            "bufferNormalized": item["bufferNorm"], "deinterleaveNormalized": item["deintNorm"], "weightedScore": item["score"],
                            "paretoOptimal": str(item["pareto"]).lower(), "weightFer": 0.40, "weightWorstStart": 0.30, "weightBuffer": 0.15, "weightDeinterleave": 0.15})
    write_csv(out_dir / "recommendation_ranking.csv", ranking_fields, ranking)
    recommendations = {scheme: next(row for row in ranking if row["scheme"] == scheme and int(row["rank"]) == 1)["configurationId"] for scheme in ("BCH", "CC")}
    (out_dir / "recommendation_summary.json").write_text(json.dumps({"status": "PASS", "recommendations": recommendations, "weights": {"meanFormalFer": 0.40, "worstHighWorkpointStartFer": 0.30, "bufferBits": 0.15, "deinterleaveTime": 0.15}, "ccInterpretationRestriction": "D8 versus PSEUDO128 is an engineering-configuration comparison; only D16 versus PSEUDO128 is controlled equal-span 128.", "mergeStatus": "NOT_MERGED"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_S7_STAGE14_ANALYSIS improvement={len(improvement)} ranking={len(ranking)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
