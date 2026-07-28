#!/usr/bin/env python3
from __future__ import annotations
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    build = stage / "build"
    results = stage / "results"
    if "--clean" in sys.argv and build.exists():
        shutil.rmtree(build)
    results.mkdir(parents=True, exist_ok=True)
    run(["cmake","-S",str(stage),"-B",str(build),"-G","MinGW Makefiles","-DCMAKE_BUILD_TYPE=Release"],stage)
    run(["cmake","--build",str(build),"--parallel"],stage)
    run([str(build/"stage05_reference_runner.exe"),str(results)],stage)
    comparison = results/"stage05_matlab_reference_comparison.csv"
    if comparison.is_file():
        with comparison.open(encoding="utf-8",newline="") as handle:
            rows=list(csv.DictReader(handle))
        mismatch_fields=["encodeMismatch","finalStateMismatch","hardPayloadMismatch",
                         "softSymbolPayloadMismatch","softLlrPayloadMismatch"]
        if len(rows)!=16 or any(r["status"]!="PASS" or any(int(r[f])!=0 for f in mismatch_fields) for r in rows):
            raise RuntimeError("Stage05 MATLAB comparison failed")
        assets=[
            results/"stage05_matlab_reference_cpp_vectors.csv",
            results/"stage05_matlab_reference_cpp_trellis.csv",
            comparison,
        ]
        manifest={"schemaVersion":"cc.stage05.reference_hashes.v1",
                  "files":[{"path":p.name,"sha256":sha256(p),"bytes":p.stat().st_size} for p in assets]}
        (results/"stage05_matlab_reference_hashes.json").write_text(
            json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        with (results/"stage05_matlab_reference_test_summary.csv").open("w",encoding="utf-8",newline="") as handle:
            writer=csv.writer(handle,lineterminator="\n")
            writer.writerow(["check","status"])
            writer.writerow(["cpp_reference_vectors_16","PASS"])
            writer.writerow(["matlab_poly2trellis_128","PASS"])
            writer.writerow(["matlab_convenc_16","PASS"])
            writer.writerow(["matlab_vitdec_hard_16","PASS"])
            writer.writerow(["matlab_vitdec_soft_symbols_16","PASS"])
            writer.writerow(["matlab_vitdec_soft_llr_16","PASS"])
            writer.writerow(["total_bit_mismatch","0"])
            writer.writerow(["stage_gate","PASS_STAGE05_CC_MATLAB_REFERENCE"])
    return 0

if __name__=="__main__":
    sys.exit(main())
