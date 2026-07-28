#!/usr/bin/env python3
import csv,math,sys
from collections import defaultdict
from pathlib import Path
def main():
 s=Path(__file__).resolve().parents[1];p=s/"results"/"stage14_block_continuous_results.csv"
 with p.open(encoding="utf-8",newline="") as h:rows=list(csv.DictReader(h))
 if len(rows)!=8:raise RuntimeError("matrix")
 g=defaultdict(list)
 for r in rows:
  g[r["rateId"]].append(r)
  if not all(math.isfinite(float(r[k])) for k in ("BER","FER","boundaryBER","avgDecodeTime_us","normalizedGoodput")):raise RuntimeError("finite")
  n=int(r["N_transmitted"]);expected=612 if r["rateId"]=="R12" else 459
  if n!=expected or not math.isclose(float(r["actualRate"]),300/n,rel_tol=1e-12):raise RuntimeError("rate")
  if int(r["tailOverheadBits"])!=6:raise RuntimeError("tail")
 for rate,v in g.items():
  if len(v)!=4:raise RuntimeError("scheme count")
  cont=v[1:]
  if len({(x["BER"],x["FER"]) for x in cont})!=1:raise RuntimeError("continuous organization changed decoder result")
  for x in cont:
   if int(x["avoidedRepeatedTailInputBits"])!=(int(x["slotCount"])-1)*6:raise RuntimeError("avoided tail")
 print("PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON");return 0
if __name__=="__main__":sys.exit(main())
