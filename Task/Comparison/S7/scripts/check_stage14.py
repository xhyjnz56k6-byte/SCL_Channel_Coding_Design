import csv
import json
import math
import sys
from pathlib import Path


def require(condition, message):
    if not condition: raise RuntimeError(message)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "stage14_fer_improvement"
    results = root / "results"
    improvements = list(csv.DictReader((results / "fer_improvement_summary.csv").open(encoding="utf-8")))
    require(len(improvements) == 8 * 31 * 3, "improvement row count mismatch")
    for row in improvements:
        require(row["pureMethodDifferenceAllowed"] == "false", "pure method claim forbidden")
        mean, base = float(row["meanPositionFer"]), float(row["baselineMeanPositionFer"])
        require(abs(float(row["absoluteFerImprovement"]) - (base - mean)) < 1e-12, "absolute improvement mismatch")
        require(abs(float(row["positionSensitivity"]) - (float(row["worstPositionFer"]) - float(row["bestPositionFer"]))) < 1e-12, "position sensitivity mismatch")
    targets = list(csv.DictReader((results / "target_fer_esn0_gain.csv").open(encoding="utf-8")))
    require(len(targets) == 8 * 3, "target FER row count mismatch")
    for row in targets:
        if row["esN0GainDb"]: require(row["configurationStatus"] == row["baselineStatus"] == "INTERPOLATED", "invalid Es/N0 gain")
    tolerance = list(csv.DictReader((results / "burst_tolerance_summary.csv").open(encoding="utf-8")))
    require(len(tolerance) == 8, "tolerance row count mismatch")
    ranking = list(csv.DictReader((results / "recommendation_ranking.csv").open(encoding="utf-8")))
    require(len(ranking) == 6, "ranking row count mismatch")
    for scheme in ("BCH", "CC"):
        group = [row for row in ranking if row["scheme"] == scheme]
        require(sorted(int(row["rank"]) for row in group) == [1, 2, 3], "ranking sequence mismatch")
        require(all(abs(sum(float(row[field]) for field in ("weightFer", "weightWorstStart", "weightBuffer", "weightDeinterleave")) - 1.0) < 1e-12 for row in group), "hidden/invalid weights")
    pseudo = next(row for row in ranking if row["configurationId"] == "CC_PSEUDO_128_RECOMMENDED")
    d8 = next(row for row in ranking if row["configurationId"] == "CC_SHORT_D8_RECOMMENDED")
    d16 = next(row for row in ranking if row["configurationId"] == "CC_SHORT_D16_CONTROL_128")
    require("ENGINEERING" in pseudo["interpretationScope"] and "ENGINEERING" in d8["interpretationScope"], "CC engineering scope missing")
    require("EQUAL_SPAN_128" in pseudo["interpretationScope"] and "EQUAL_SPAN_128" in d16["interpretationScope"], "CC controlled scope missing")
    report = {"status": "PASS", "improvementRows": len(improvements), "targetRows": len(targets), "toleranceRows": len(tolerance), "rankingRows": len(ranking), "mergeStatus": "NOT_MERGED"}
    (results / "stage14_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_S7_STAGE14")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE14: {error}", file=sys.stderr)
        raise
