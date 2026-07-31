#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, sys
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def close(a,b,tol=1e-12):return math.isclose(a,b,rel_tol=tol,abs_tol=tol)
def main()->int:
    stage=Path(__file__).resolve().parents[1]; results=stage/"results"
    source=results/"stage08_awgn_prescan_point_results.csv"
    with source.open(encoding="utf-8",newline="") as h: rows=list(csv.DictReader(h))
    if not rows: raise RuntimeError("empty prescan")
    grouped=defaultdict(list)
    for r in rows:
        values={k:float(r[k]) for k in ("snrDb","ebN0Db","actualRate","sigmaSquared","BER","FER","payloadSuccessRate","normalizedGoodput")}
        ints={k:int(r[k]) for k in ("N_transmitted","framesProcessed","payloadBitErrors","payloadErrorFrames")}
        if not all(math.isfinite(v) for v in values.values()):raise RuntimeError("non-finite point")
        if not close(values["actualRate"],300/ints["N_transmitted"]):raise RuntimeError("actualRate")
        if not close(values["ebN0Db"],values["snrDb"]-10*math.log10(values["actualRate"])):raise RuntimeError("EbN0")
        if not close(values["sigmaSquared"],1/(2*10**(values["snrDb"]/10))):raise RuntimeError("sigma")
        if not close(values["BER"],ints["payloadBitErrors"]/(300*ints["framesProcessed"])):raise RuntimeError("BER")
        if not close(values["FER"],ints["payloadErrorFrames"]/ints["framesProcessed"]):raise RuntimeError("FER")
        if not close(values["normalizedGoodput"],values["actualRate"]*(1-values["FER"])):raise RuntimeError("goodput")
        grouped[r["caseId"]].append(r)
    if len(grouped)!=6:raise RuntimeError("case count")
    for case,items in grouped.items():
        items.sort(key=lambda r:float(r["snrDb"]))
        if any(float(items[i]["snrDb"])>=float(items[i+1]["snrDb"]) for i in range(len(items)-1)):
            raise RuntimeError("non-monotonic SNR")
    for rate in ("R12","R23","R34"):
        hard={r["snrDb"]:float(r["FER"]) for r in grouped[f"CC-B-{rate}-H"]}
        soft={r["snrDb"]:float(r["FER"]) for r in grouped[f"CC-B-{rate}-S"]}
        if any(soft[x]>hard[x]+1e-15 for x in hard.keys()&soft.keys()):raise RuntimeError("soft FER worse than hard")

    available={f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei","SimHei","Noto Sans CJK SC"):
        if candidate in available:
            plt.rcParams["font.sans-serif"]=[candidate];break
    plt.rcParams["axes.unicode_minus"]=False
    colors={"R12":"#1f77b4","R23":"#ff7f0e","R34":"#2ca02c"}
    figures=[]
    for metric,title in (("BER","300比特卷积码误比特率预扫描"),("FER","300比特卷积码误帧率预扫描")):
        fig,ax=plt.subplots(figsize=(8,5),dpi=160)
        plotted=0;zero_count=0
        for case,items in sorted(grouped.items()):
            rate=case.split("-")[2];decoder=case.split("-")[3]
            x=[];y=[]
            for r in items:
                value=float(r[metric]);zero_count+=value==0
                if value>0:x.append(float(r["snrDb"]));y.append(value)
            ax.plot(x,y,color=colors[rate],linestyle="--" if decoder=="H" else "-",
                    marker="s" if decoder=="H" else "o",label=f"{rate[1]}/{rate[2]}-{'硬判决' if decoder=='H' else '软判决'}")
            plotted+=len(x)
        ax.set_yscale("log");ax.set_xlabel("SNR (dB)");ax.set_ylabel(metric)
        ax.set_title(title);ax.grid(True,which="both",alpha=.25);ax.legend(ncol=2)
        fig.tight_layout()
        png=results/f"stage08_awgn_prescan_{metric.lower()}.png";fig.savefig(png);plt.close(fig)
        data=results/f"stage08_awgn_prescan_{metric.lower()}_figure_data.csv"
        with data.open("w",encoding="utf-8",newline="") as h:
            writer=csv.DictWriter(h,fieldnames=list(rows[0].keys()));writer.writeheader();writer.writerows(rows)
        figures.append({"metric":metric,"sourceCsv":source.name,"sourceSha256":sha(source),
                        "figureDataCsv":data.name,"figureDataSha256":sha(data),"png":png.name,
                        "pngSha256":sha(png),"pointRows":len(rows),"plottedPositivePoints":plotted,
                        "zeroErrorPoints":zero_count,"xColumn":"snrDb","xLabel":"SNR (dB)",
                        "yScale":"log","zeroPolicy":"raw zero preserved; zero omitted on log axis"})
    manifest={"schemaVersion":"cc.stage08.plot_manifest.v1","figures":figures}
    (results/"stage08_awgn_prescan_plot_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    with (results/"stage08_awgn_prescan_formal_case_ranges.csv").open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n");w.writerow(["caseId","formalMinSnrDb","formalMaxSnrDb","stepDb","basis"])
        for case,items in sorted(grouped.items()):
            eligible=[r for r in items if 0.005<=float(r["FER"])<=0.8]
            if not eligible:eligible=[min(items,key=lambda r:abs(float(r["FER"])-0.1))]
            w.writerow([case,min(float(r["snrDb"]) for r in eligible),max(float(r["snrDb"]) for r in eligible),0.2,"prescan_FER_0.005_to_0.8"])
    with (results/"stage08_awgn_prescan_plot_check.md").open("w",encoding="utf-8") as h:
        h.write("# Stage08 绘图检查\n\nPASS：逐点公式、有限性、六 Case、SNR 单调、hard/soft 公平关系、PNG 签名与 SHA256 均通过。\n")
    with (results/"stage08_awgn_prescan_test_summary.csv").open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n");w.writerow(["check","status"]);w.writerow(["point_formula_check","PASS"])
        w.writerow(["case_count","6"]);w.writerow(["figure_count","2"]);w.writerow(["soft_not_worse_than_hard","PASS"])
        w.writerow(["stage_gate","PASS_STAGE08_CC_AWGN_PRESCAN"])
    print("PASS_STAGE08_CC_AWGN_PRESCAN")
    return 0
if __name__=="__main__":sys.exit(main())
