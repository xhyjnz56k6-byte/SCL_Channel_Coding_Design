import csv
import json
import math
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "stage13_latency_complexity"
    path = root / "results" / "latency_complexity_summary.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    require(len(rows) == 8, "expected eight BCH/CC configurations")
    require({row["scheme"] for row in rows} == {"BCH", "CC"}, "scheme set mismatch")
    for row in rows:
        require(int(row["formalPointCount"]) == 558, "formal point count mismatch")
        require(row["pureMethodDifferenceAllowed"] == "false", "pure method claim forbidden")
        require(row["physicalLatencyClaimAllowed"] == "false", "physical latency claim forbidden")
        require(float(row["additionalCpuTimeMeanNsWeighted"]) == float(row["interleaveTimeMeanNsWeighted"]) + float(row["deinterleaveTimeMeanNsWeighted"]), "additional CPU mismatch")
        require(float(row["bufferFractionOfFrame"]) >= 0 and math.isfinite(float(row["decodeTimeMeanNsWeighted"])), "invalid metric")
        require(Path(row["sourceAbsolutePath"]).is_file(), "source absolute path missing")
        if row["comparisonRole"] == "BASELINE": require(int(row["startupDelayBits"]) == 0 and int(row["startupDelayTrellisSteps"]) == 0, "baseline startup delay must be zero")
        if row["configurationId"] == "CC_SHORT_D8_RECOMMENDED": require(int(row["spanTrellisSteps"]) == 64, "D8 span mismatch")
        if row["configurationId"] in ("CC_PSEUDO_128_RECOMMENDED", "CC_SHORT_D16_CONTROL_128"): require(int(row["spanTrellisSteps"]) == 128, "controlled span mismatch")
    report = {"status": "PASS", "rowCount": len(rows), "sourceCount": 2, "physicalLatencyClaims": 0, "mergeStatus": "NOT_MERGED"}
    (root / "results" / "stage13_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_S7_STAGE13 rows=8")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE13: {error}", file=sys.stderr)
        raise
