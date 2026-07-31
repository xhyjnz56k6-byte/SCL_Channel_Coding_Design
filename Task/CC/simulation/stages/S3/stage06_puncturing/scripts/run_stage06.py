#!/usr/bin/env python3
from __future__ import annotations
import csv, json, shutil, subprocess, sys
from pathlib import Path
def run(c,cwd): print("+"," ".join(c)); subprocess.run(c,cwd=cwd,check=True)
def main():
    stage=Path(__file__).resolve().parents[1]; build=stage/"build"; results=stage/"results"
    if "--clean" in sys.argv and build.exists(): shutil.rmtree(build)
    results.mkdir(parents=True,exist_ok=True)
    run(["cmake","-S",str(stage),"-B",str(build),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],stage)
    run(["cmake","--build",str(build),"--parallel"],stage)
    run(["ctest","--test-dir",str(build),"--output-on-failure"],stage)
    matlab=results/"stage06_puncturing_matlab_comparison.csv"
    if matlab.is_file():
        with matlab.open(encoding="utf-8",newline="") as h: rows=list(csv.DictReader(h))
        if len(rows)!=4 or any(r["status"]!="PASS" for r in rows): raise RuntimeError("MATLAB mismatch")
        with (results/"stage06_puncturing_candidate_prescan.csv").open(encoding="utf-8",newline="") as h:
            stats=list(csv.DictReader(h))
        chosen={}
        for rate,prefix in (("2/3","R23_"),("3/4","R34_")):
            candidates=[r for r in stats if r["patternId"].startswith(prefix)]
            best=min(candidates,key=lambda r:(int(r["softFrameErrors"]),int(r["hardFrameErrors"]),r["patternId"]))
            chosen[rate]=best["patternId"]
        (results/"stage06_puncturing_selection.json").write_text(json.dumps(chosen,indent=2)+"\n",encoding="utf-8")
        with (results/"stage06_puncturing_test_summary.csv").open("w",encoding="utf-8",newline="") as h:
            w=csv.writer(h,lineterminator="\n"); w.writerow(["check","status"])
            w.writerow(["noiseless_four_patterns_480_frames","PASS"])
            w.writerow(["phase_carry","PASS"]); w.writerow(["matlab_four_patterns","PASS"])
            w.writerow(["selectedR23",chosen["2/3"]]); w.writerow(["selectedR34",chosen["3/4"]])
            w.writerow(["stage_gate","PASS_STAGE06_CC_PUNCTURING"])
    return 0
if __name__=="__main__": sys.exit(main())
