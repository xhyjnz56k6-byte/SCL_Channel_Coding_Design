import csv, hashlib, json, platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="Microsoft YaHei"; plt.rcParams["axes.unicode_minus"]=False

STAGE=Path(__file__).resolve().parents[1]; RESULTS=STAGE/"results"; PLOTS=STAGE/"plots"
SOURCE=RESULTS/"stage06_awgn_formal_results.csv"
STYLE={"STYLE_1":("#1f77b4","-","o"),"STYLE_2":("#ff7f0e","--","s"),
       "STYLE_3":("#2ca02c","-.","^"),"STYLE_4":("#d62728",":","D")}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with path.open(newline="",encoding="utf-8-sig") as stream:return list(csv.DictReader(stream))
def write(path,rows):
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def main():
    PLOTS.mkdir(parents=True,exist_ok=True); raw=read(SOURCE); aggregate=[]; figures=[]
    for payload,tag in ((200,"k200"),(300,"k300")):
      selected=[r for r in raw if int(r["payloadLength"])==payload]
      for metric,title,ylabel,logscale in (("ber","误码率","BER",True),("fer","误帧率","FER",True),
                                           ("decodeTimeMeanNs","译码时延","译码时延 (μs)",False)):
        fid=f"stage06_awgn_formal_{tag}_{'latency' if metric.startswith('decode') else metric}"
        data=[]
        for r in selected:
            denominator=int(r["totalPayloadBits"] if metric=="ber" else r["totalFrames"])
            raw_y=float(r[metric])/1000.0 if metric.startswith("decode") else float(r[metric])
            zero=logscale and raw_y==0.0; plot_y=0.5/denominator if zero else raw_y
            data.append({"figureId":fid,"caseId":r["caseId"],"legendLabel":r["legendLabel"],
              "styleId":r["styleId"],"metric":ylabel,"ebn0Index":r["ebn0Index"],"ebn0Db":r["ebn0Db"],
              "actualRate":r["actualRate"],"snrLinear":r["snrLinear"],"snrDb":r["snrDb"],
              "rawY":format(raw_y,".17g"),"plotY":format(plot_y,".17g"),"denominator":denominator,
              "zeroSurrogateApplied":str(zero).lower(),"zeroSurrogateRule":"0.5/denominator"})
        data.sort(key=lambda x:(x["caseId"],int(x["ebn0Index"]))); aggregate+=data
        dp=PLOTS/f"{fid}_figure_data.csv";write(dp,data)
        fig,ax=plt.subplots(figsize=(7.2,5.2))
        for case in dict.fromkeys(x["caseId"] for x in data):
            pts=[x for x in data if x["caseId"]==case]; color,line,marker=STYLE[pts[0]["styleId"]]
            ax.plot([float(x["snrDb"]) for x in pts],[float(x["plotY"]) for x in pts],
                    color=color,linestyle=line,marker=marker,label=pts[0]["legendLabel"])
        ax.set(xlabel="SNR (dB)",ylabel=ylabel,title=f"{payload}比特BCH正式{title}")
        if logscale:ax.set_yscale("log")
        ax.grid(True,which="both",linestyle=":",linewidth=.6);ax.legend(loc="upper right");fig.tight_layout()
        png=PLOTS/f"{fid}.png";fig.savefig(png,dpi=300,format="png");plt.close(fig)
        figures.append({"figureId":fid,"png":png.name,"figureData":dp.name,"dpi":300,
                        "xAxis":"SNR (dB)","pngSha256":sha(png),"figureDataSha256":sha(dp)})
    aggregate_path=PLOTS/"stage06_awgn_formal_figure_data.csv";write(aggregate_path,aggregate)
    manifest={"stageId":"stage06_awgn_formal","sourceResultsSha256":sha(SOURCE),
      "plotScriptSha256":sha(Path(__file__)),"pythonVersion":platform.python_version(),
      "matplotlibVersion":matplotlib.__version__,"zeroSurrogateRule":"0.5/denominator",
      "aggregateFigureData":aggregate_path.name,"aggregateFigureDataSha256":sha(aggregate_path),
      "figures":figures}
    (PLOTS/"stage06_awgn_formal_plot_manifest.json").write_text(
      json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS_STAGE06_AWGN_FORMAL_PLOT")
if __name__=="__main__":main()
