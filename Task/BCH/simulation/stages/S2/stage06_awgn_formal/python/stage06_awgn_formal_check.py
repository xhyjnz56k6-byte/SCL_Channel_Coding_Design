import csv,json,math
from collections import Counter
from pathlib import Path
STAGE=Path(__file__).resolve().parents[1];RESULTS=STAGE/"results";LOGS=STAGE/"logs";PLOTS=STAGE/"plots"
CASES={"K200_S15","K200_M255K207","K200_M511K421","K200_M511K385",
       "K300_S15","K300_M255K207","K300_M511K421","K300_M511K385"}
def rows(path):
    with path.open(newline="",encoding="utf-8-sig") as stream:return list(csv.DictReader(stream))
def req(value,message):
    if not value:raise SystemExit("BLOCKED_STAGE06_AWGN_FORMAL_CHECK: "+message)
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-11)
def main():
    config=json.loads((STAGE/"configs/stage06_awgn_formal_config.json").read_text(encoding="utf-8"))
    req(set(config["points"])==CASES and all(len(x)==5 for x in config["points"].values()),"grid mismatch")
    req(config["stopRule"]=={"minFrames":5000,"targetFrameErrors":200,"maxFrames":50000},"stop rule mismatch")
    data=rows(RESULTS/"stage06_awgn_formal_results.csv");req(len(data)==40,"not 40 points")
    for r in data:
        f=int(r["totalFrames"]);e=int(r["payloadErrorFrames"]);bits=int(r["totalPayloadBits"])
        req(5000<=f<=50000,"frame limit");req(int(r["trueSuccessFrames"])+e==f,"accounting")
        if r["stopReason"]=="TARGET_FRAME_ERRORS_REACHED":req(e>=200,"target stop without target")
        elif r["stopReason"]=="MAX_FRAMES_REACHED":req(f==50000 and e<200,"max stop invalid")
        else:req(False,"unknown stop reason")
        req(close(r["ber"],int(r["payloadErrorBits"])/bits) and close(r["fer"],e/f),"rate mismatch")
        rate=float(r["actualRate"]);eb=float(r["ebn0Db"]);sigma=1/(2*rate*10**(eb/10))
        req(close(r["sigma2"],sigma) and close(r["snrDb"],eb+10*math.log10(2*rate)),"AWGN formula")
        req(all(math.isfinite(float(r[x])) for x in ("ber","fer","decodeTimeMeanNs","decodeTimeP99Ns")),"NaN Inf")
    req(len(list((RESULTS/"checkpoints").glob("*.json")))==40,"checkpoint count")
    req(len(rows(RESULTS/"stage06_awgn_formal_shard_manifest.csv"))==40,"shard manifest")
    req(all(r["passed"] in ("1","true") for r in rows(RESULTS/"stage06_awgn_formal_merge_audit.csv")),"merge audit")
    manifest=json.loads((PLOTS/"stage06_awgn_formal_plot_manifest.json").read_text(encoding="utf-8"))
    req(len(manifest["figures"])==6 and len(rows(PLOTS/"stage06_awgn_formal_figure_data.csv"))==120,"plot data")
    for fig in manifest["figures"]:
        req((PLOTS/fig["png"]).read_bytes()[:8]==b"\x89PNG\r\n\x1a\n" and fig["dpi"]==300,"PNG contract")
        req(len(rows(PLOTS/fig["figureData"]))==20,"figure rows")
    req("100% tests passed" in (LOGS/"stage06_awgn_formal_ctest.log").read_text(encoding="utf-8"),"CTest")
    req("PASS_STAGE06_AWGN_FORMAL_RUNNER" in (LOGS/"stage06_awgn_formal_runner.log").read_text(encoding="utf-8"),"runner")
    req("PASS_STAGE06_AWGN_FORMAL_PLOT" in (LOGS/"stage06_awgn_formal_plot.log").read_text(encoding="utf-8"),"plot")
    reasons=Counter(r["stopReason"] for r in data)
    (STAGE/"stage06_awgn_formal_result_summary.csv").write_text(
      "metric,value\nformalPoints,40\ntotalFrames,"+str(sum(int(r["totalFrames"]) for r in data))+
      "\ntargetStops,"+str(reasons["TARGET_FRAME_ERRORS_REACHED"])+"\nmaxStops,"+
      str(reasons["MAX_FRAMES_REACHED"])+"\nplots,6\n",encoding="utf-8")
    print("PASS_STAGE06_AWGN_FORMAL")
    print("PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06")
if __name__=="__main__":main()
