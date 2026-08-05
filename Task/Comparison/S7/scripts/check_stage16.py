import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition: raise RuntimeError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks=[
        [sys.executable,str(ROOT/"scripts"/"check_stage01_09.py")],
        [sys.executable,str(ROOT/"scripts"/"check_formal.py"),"BCH",str(ROOT/"stage10_bch_formal"/"results")],
        [sys.executable,str(ROOT/"scripts"/"check_formal.py"),"CC",str(ROOT/"stage11_cc_formal"/"results")],
        [sys.executable,str(ROOT/"scripts"/"check_stage12.py")],
        [sys.executable,str(ROOT/"scripts"/"check_stage13.py")],
        [sys.executable,str(ROOT/"scripts"/"check_stage14.py")],
        [sys.executable,str(ROOT/"scripts"/"check_stage15.py")]]
    outputs=[]
    for command in checks:
        result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8")
        require(result.returncode==0,f"sub-gate failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")
        outputs.append(result.stdout.strip())
    for directory in ROOT.rglob("*"):
        if not directory.is_dir() or (ROOT/"build" in directory.parents) or directory==ROOT/"build": continue
        require((directory/"readme.txt").is_file(),f"missing directory readme: {directory.relative_to(ROOT)}")
    results=list(csv.DictReader((ROOT/"S7_result_inventory.csv").open(encoding="utf-8")))
    require(len(results)==9 and all(Path(row["absolutePath"]).is_file() for row in results),"result inventory mismatch")
    plots=list(csv.DictReader((ROOT/"S7_plot_inventory.csv").open(encoding="utf-8"))); require(len(plots)==50,"plot inventory mismatch")
    metrics=list(csv.DictReader((ROOT/"S7_metric_summary.csv").open(encoding="utf-8"))); require(len(metrics)==8,"metric summary mismatch")
    ldpc=list(csv.DictReader((ROOT/"results"/"ldpc_baseline"/"ldpc_baseline_reference.csv").open(encoding="utf-8")))
    require(len(ldpc)==62 and all(row["s7ChannelCompatibility"].startswith("INCOMPATIBLE") for row in ldpc),"LDPC restriction mismatch")
    for line in (ROOT/"S7_sha256.txt").read_text(encoding="utf-8").splitlines():
        expected,relative=line.split("  ",1); path=ROOT/relative; require(path.is_file() and digest(path)==expected,f"top-level SHA mismatch: {relative}")
    forbidden=("Pending","PENDING","to be run","NOT_PUSHED","TO_VERIFY_AFTER_PUSH")
    for name in ("S7_final_report.md","S7_validation_report.md","S7_manifest.json"):
        text=(ROOT/name).read_text(encoding="utf-8"); require(not any(token in text for token in forbidden),f"unfinished token in {name}")
    report={"status":"PASS","subGates":outputs,"resultInventoryRows":len(results),"plotCount":len(plots),"metricRows":len(metrics),"ldpcReferenceRows":len(ldpc),"mergeStatus":"NOT_MERGED"}
    (ROOT/"stage16_final_integration"/"results"/"stage16_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS_S7_STAGE16_FINAL_AUDIT")
    return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE16: {error}",file=sys.stderr); raise
