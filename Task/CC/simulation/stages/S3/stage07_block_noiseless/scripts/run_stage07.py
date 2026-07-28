#!/usr/bin/env python3
from __future__ import annotations
import csv, shutil, subprocess, sys
from pathlib import Path
def run(c,cwd): print("+"," ".join(c)); subprocess.run(c,cwd=cwd,check=True)
def main():
    stage=Path(__file__).resolve().parents[1]; build=stage/"build"; results=stage/"results"
    if "--clean" in sys.argv and build.exists(): shutil.rmtree(build)
    results.mkdir(parents=True,exist_ok=True)
    run(["cmake","-S",str(stage),"-B",str(build),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],stage)
    run(["cmake","--build",str(build),"--parallel"],stage)
    run(["ctest","--test-dir",str(build),"--output-on-failure"],stage)
    with (results/"stage07_block_noiseless_case_results.csv").open(encoding="utf-8",newline="") as h:
        rows=list(csv.DictReader(h))
    if len(rows)!=6 or any(int(r["payloadBitMismatch"]) or int(r["payloadFrameMismatch"]) or int(r["nonFiniteMetricCount"]) for r in rows):
        raise RuntimeError("Stage07 case mismatch")
    expected={"R12":612,"R23":459,"R34":408}
    for r in rows:
        rate=r["caseId"].split("-")[2]
        if int(r["N_transmitted"])!=expected[rate] or int(r["observedMaskCount"])!=expected[rate]:
            raise RuntimeError("Stage07 length/mask mismatch")
    with (results/"stage07_block_noiseless_test_summary.csv").open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n"); w.writerow(["check","status"])
        w.writerow(["six_cases_100_frames_each","PASS"]);w.writerow(["payloadBitMismatch","0"])
        w.writerow(["payloadFrameMismatch","0"]);w.writerow(["nonFiniteMetricCount","0"])
        w.writerow(["checkpoint_basic_roundtrip","PASS"]);w.writerow(["stage_gate","PASS_STAGE07_CC_BLOCK_NOISELESS"])
    return 0
if __name__=="__main__":sys.exit(main())
