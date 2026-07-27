import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7];STAGE=Path(__file__).resolve().parents[1]
def req(value,message):
    if not value:raise SystemExit("BLOCKED_STAGE06_AWGN_FORMAL_AUDIT: "+message)
def git(*args):
    result=subprocess.run(["git",*args],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    req(result.returncode==0,result.stderr.strip());return result.stdout.strip()
def main():
    manifest=json.loads((STAGE/"stage06_awgn_formal_manifest.json").read_text(encoding="utf-8"))
    req(git("branch","--show-current")==manifest["branch"],"branch mismatch")
    req(manifest["gate"]=="PASS_STAGE06_AWGN_FORMAL" and
        manifest["overallGate"]=="PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06","Gate mismatch")
    req(manifest["mergeStatus"]=="NOT_MERGED","merge status")
    item=manifest["functionalRanges"][0];actual=[]
    for line in git("diff","--name-status",item["baseCommit"],item["contentCommit"]).splitlines():
        fields=line.split("\t");req(fields[0]=="A","unexpected diff "+line);actual.append(fields[-1])
    req(actual==item["files"],"manifest differs from functional diff")
    req(all(x.startswith("Task/BCH/simulation/stages/S2/stage06_awgn_formal/") for x in actual),"scope")
    req(not any(x.endswith((".exe",".obj",".pdb")) or "/build/" in x for x in actual),"binary")
    for relative in manifest["generatedEvidence"]:
        path=STAGE/relative;req(path.exists() and path.stat().st_size>0,"missing "+relative)
    validation=(STAGE/"stage06_awgn_formal_validation_report.md").read_text(encoding="utf-8")
    for token in ("Pending","to be run","NOT_PUSHED","TO_VERIFY_AFTER_PUSH"):req(token not in validation,token)
    req((STAGE/"stage06_awgn_formal_changes.patch").stat().st_size>0,"empty patch")
    user_plan="Task/BCH/Plan/第3组计划/v2.0-BCH信道多干扰实验重做.md"
    req((ROOT/user_plan).exists() and git("ls-files","--others","--exclude-standard","--",user_plan)!="",
        "user plan not preserved")
    print("PASS_STAGE06_AWGN_FORMAL_AUDIT")
    print("PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06")
if __name__=="__main__":main()
