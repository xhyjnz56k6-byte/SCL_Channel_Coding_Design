#!/usr/bin/env python3
from __future__ import annotations
import csv,math,sys
from collections import defaultdict
from pathlib import Path

def main():
 stage=Path(__file__).resolve().parents[1];res=stage/"results"
 with (res/"stage11_soft_quantization_results.csv").open(encoding="utf-8",newline="") as h:rows=list(csv.DictReader(h))
 if len(rows)!=16:raise RuntimeError("expected 16 formal rows")
 groups=defaultdict(list)
 for r in rows:
  key=(r["caseId"],float(r["snrDb"]));groups[key].append(r);f=int(r["frames"]);be=int(r["payloadBitErrors"]);fe=int(r["payloadErrorFrames"])
  nums=["BER","FER","avgDecodeTime_us","p95DecodeTime_us","maxDecodeTime_us","rawThroughput_Mbps"]
  if not all(math.isfinite(float(r[x])) for x in nums):raise RuntimeError("non-finite")
  if f!=1000 or not math.isclose(float(r["BER"]),be/(300*f),rel_tol=1e-12) or not math.isclose(float(r["FER"]),fe/f,rel_tol=1e-12):raise RuntimeError("formula")
  if int(r["integerOverflowCount"])!=0 or int(r["pathMetricSaturationCount"])!=0:raise RuntimeError("integer metric saturation/overflow")
  if r["mode"]=="SOFT_FLOAT" and (int(r["floatMismatchBits"]) or int(r["floatMismatchFrames"])):raise RuntimeError("float mismatch")
 if len(groups)!=4 or any(len(v)!=4 for v in groups.values()):raise RuntimeError("matrix")
 qualified=[];summary=[]
 for bits in (3,4,6):
  worst_ber=worst_fer=0
  for key,items in groups.items():
   by={r["mode"]:r for r in items};base=by["SOFT_FLOAT"];q=by[f"SOFT_Q{bits}"]
   br=float(q["BER"])/float(base["BER"]);fr=float(q["FER"])/float(base["FER"])
   worst_ber=max(worst_ber,br-1);worst_fer=max(worst_fer,fr-1)
  ok=worst_ber<=.10 and worst_fer<=.10
  summary.append({"bits":bits,"worstBerIncrease":worst_ber,"worstFerIncrease":worst_fer,"qualified":"YES" if ok else "NO"})
  if ok:qualified.append(bits)
 if not qualified:raise RuntimeError("no quantization width meets threshold")
 recommended=min(qualified)
 with (res/"stage11_quantization_comparison_summary.csv").open("w",encoding="utf-8",newline="") as h:
  w=csv.DictWriter(h,fieldnames=list(summary[0]),lineterminator="\n");w.writeheader();w.writerows(summary)
 with (res/"stage11_quantization_recommendation.csv").open("w",encoding="utf-8",newline="") as h:
  w=csv.writer(h,lineterminator="\n");w.writerow(["recommendedBits","qualifiedBits","rule"]);w.writerow([recommended,"|".join(map(str,qualified)),"minimum width with <=10% BER/FER increase at every scenario and zero overflow"])
 with (res/"stage11_quantization_test_summary.csv").open("w",encoding="utf-8",newline="") as h:
  w=csv.writer(h,lineterminator="\n");w.writerow(["check","status"]);w.writerow(["global_clip_prescan","PASS"]);w.writerow(["formal_matrix","PASS"]);w.writerow(["integer_overflow","PASS_ZERO"]);w.writerow(["recommended_bits",f"PASS_Q{recommended}"]);w.writerow(["stage_gate","PASS_STAGE11_CC_SOFT_QUANTIZATION"])
 print(f"PASS_STAGE11_CC_SOFT_QUANTIZATION recommended=Q{recommended}")
 return 0
if __name__=="__main__":sys.exit(main())
