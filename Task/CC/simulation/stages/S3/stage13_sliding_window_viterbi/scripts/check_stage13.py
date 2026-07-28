#!/usr/bin/env python3
import csv,math,sys
from pathlib import Path
def main():
 s=Path(__file__).resolve().parents[1];r=s/"results"
 with (r/"stage13_sliding_window_results.csv").open(encoding="utf-8",newline="") as h:rows=list(csv.DictReader(h))
 if len(rows)!=2:raise RuntimeError("formal case count")
 for x in rows:
  for k in ("BER","FER","avgDecisionDelayBits","maxDecisionDelayBits","avgDecodeTime_us"):
   if not math.isfinite(float(x[k])):raise RuntimeError("nonfinite")
  if int(x["frames"])!=500 or int(x["firstOutputInputTime"])<69:raise RuntimeError("warmup")
  if int(x["headMismatchBits"])+int(x["boundaryMismatchBits"])+int(x["middleMismatchBits"])+int(x["tailMismatchBits"])!=int(x["fullMismatchBits"]):raise RuntimeError("region mismatch sum")
 with (r/"stage13_output_bit_metadata.csv").open(encoding="utf-8",newline="") as h:m=list(csv.DictReader(h))
 for case in {x["caseId"] for x in rows}:
  v=[x for x in m if x["caseId"]==case];idx=[int(x["bitIndex"]) for x in v]
  if idx!=list(range(300)) or any(int(x["decisionTimeInputBit"])<int(x["receiveTimeInputBit"]) for x in v):raise RuntimeError("output metadata")
 print("PASS_STAGE13_CC_SLIDING_WINDOW");return 0
if __name__=="__main__":sys.exit(main())
