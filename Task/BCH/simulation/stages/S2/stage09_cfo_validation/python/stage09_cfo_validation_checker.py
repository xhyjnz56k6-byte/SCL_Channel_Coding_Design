import csv
import math
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"

def rows(name):
    with (RESULTS / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

fixed = rows("stage09_cfo_validation_fixed_vectors.csv")
cpp = rows("stage09_cfo_validation_cpp_outputs.csv")
mat = rows("stage09_cfo_validation_matlab_outputs.csv")
assert len(fixed) == len(cpp) == len(mat) == 4
comparison = []
for src, c, m in zip(fixed, cpp, mat):
    assert src["vectorId"] == c["vectorId"] == m["vectorId"]
    errors = [abs(float(c[key]) - float(m[key]))
              for key in ("phaseRad", "realValue", "imagValue")]
    bit_mismatch = int(c["hardBit"]) != int(float(m["hardBit"]))
    assert max(errors) <= 1e-12 and not bit_mismatch
    comparison.append({
        "vectorId": c["vectorId"], "k": c["k"],
        "maxContinuousError": f"{max(errors):.17g}",
        "bitMismatch": int(bit_mismatch), "passed": 1})
with (RESULTS / "stage09_cfo_validation_comparison.csv").open(
        "w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=comparison[0].keys())
    writer.writeheader()
    writer.writerows(comparison)
case_rows = rows("stage09_cfo_validation_case_results.csv")
assert len(case_rows) == 8
for row in case_rows:
    n = int(row["encodedLength"])
    delta = float(row["deltaPhaseRadPerSymbol"])
    assert abs(delta - math.radians(30)/(n-1)) <= 1e-15
    assert abs(float(row["firstPhaseRad"])) <= 1e-15
    assert abs(float(row["lastPhaseRad"]) - math.pi/6) <= 1e-12
    assert row["resumePass"] == row["shardMergePass"] == "1"
print("PASS_STAGE09_CFO_VALIDATION")
