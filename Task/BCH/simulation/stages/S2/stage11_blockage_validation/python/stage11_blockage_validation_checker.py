import csv, math
from pathlib import Path
STAGE=Path(__file__).resolve().parents[1]; R=STAGE/"results"
def read(name):
 with (R/name).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
cpp=read("stage11_blockage_validation_cpp_outputs.csv")
mat=read("stage11_blockage_validation_matlab_outputs.csv")
assert len(cpp)==len(mat)==8
comparison=[]
for a,b in zip(cpp,mat):
 err=abs(float(a["received"])-float(b["received"]))
 mismatch=int(a["hardBit"])!=int(float(b["hardBit"]))
 mask=int(a["isBlocked"])!=int(float(b["isBlocked"]))
 assert err<=1e-12 and not mismatch and not mask
 comparison.append({"vectorId":a["vectorId"],"k":a["k"],"continuousError":err,
                    "maskMismatch":int(mask),"bitMismatch":int(mismatch),"passed":1})
with (R/"stage11_blockage_validation_comparison.csv").open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=comparison[0]);w.writeheader();w.writerows(comparison)
cases=read("stage11_blockage_validation_case_results.csv");assert len(cases)==8
for r in cases:
 n=int(r["encodedLength"]);l=int(r["blockageLengthSymbols"])
 assert l==math.floor(.1*n+.5)
 assert abs(float(r["actualBlockageRatio"])-l/n)<=1e-12
 assert 0<=int(r["minStart"])<=int(r["maxStart"])<=n-l
 assert r["resumePass"]==r["shardMergePass"]=="1"
stats=read("stage11_blockage_validation_statistics.csv")[0]
assert .48<=float(stats["blockedRawBer"])<=.52
print("PASS_STAGE11_BLOCKAGE_VALIDATION")
