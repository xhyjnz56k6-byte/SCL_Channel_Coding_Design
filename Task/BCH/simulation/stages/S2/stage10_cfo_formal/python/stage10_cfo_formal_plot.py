import csv, hashlib, json
from pathlib import Path
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"]=False

STAGE=Path(__file__).resolve().parents[1]; RESULTS=STAGE/"results"
PLOTS=STAGE/"plots"; MANIFESTS=STAGE/"manifests"
PLOTS.mkdir(exist_ok=True); MANIFESTS.mkdir(exist_ok=True)
source=RESULTS/"stage10_cfo_formal_result_summary.csv"
with source.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
styles={
"K200_S15":("分块","#0072B2","-","o"),"K200_M255K207":("255整块","#D55E00","--","s"),
"K200_M511K421":("421整块","#009E73","-.", "^"),"K200_M511K385":("385整块","#CC79A7",":","D"),
"K300_S15":("分块","#0072B2","-","o"),"K300_M255K207":("255双块","#D55E00","--","s"),
"K300_M511K421":("421整块","#009E73","-.","^"),"K300_M511K385":("385整块","#CC79A7",":","D")}
metrics=[("ber","BER",True),("fer","FER",True),("miscorrectionRate","误纠率",True),
         ("decodeTimeMeanNs","译码时延",False)]
title_labels={"ber":"误码率","fer":"误帧率","miscorrectionRate":"误纠率",
              "decodeTimeMeanNs":"译码时延"}
for payload in (200,300):
  for metric,ylabel,logy in metrics:
    selected=[r for r in rows if int(r["payloadLength"])==payload]
    figure_rows=[]
    plt.figure(figsize=(7.2,4.8))
    for case in [c for c in styles if c.startswith(f"K{payload}")]:
      group=sorted((r for r in selected if r["caseId"]==case),key=lambda r:float(r["snrDb"]))
      label,color,line,marker=styles[case]
      xs=[float(r["snrDb"]) for r in group]; raw=[float(r[metric]) for r in group]
      plot=[v if v>0 or not logy else (0.5/(int(r["totalPayloadBits"]) if metric=="ber" else int(r["totalFrames"])))
            for v,r in zip(raw,group)]
      plt.plot(xs,plot,label=label,color=color,linestyle=line,marker=marker,linewidth=1.5)
      for r,v,p in zip(group,raw,plot):
        figure_rows.append({"caseId":case,"legendLabel":label,"payloadLength":payload,
          "encodedLength":r["encodedLength"],"actualRate":r["actualRate"],
          "ebn0Db":r["ebn0Db"],"snrDb":r["snrDb"],"targetSnrDb":r["snrDb"],"metricName":metric,
          "metricValue":f"{v:.17g}","totalFrames":r["totalFrames"],
          "errorCount":r["payloadErrorBits"] if metric=="ber" else
                       r["payloadErrorFrames"] if metric=="fer" else r["miscorrectionFrames"],
          "isZeroObserved":int(v==0),"plotSurrogateUsed":int(v==0 and logy),
          "plotValue":f"{p:.17g}"})
    plt.xlabel("SNR"); plt.ylabel(ylabel); plt.title(f"{payload}比特BCH{title_labels[metric]}对比")
    if logy: plt.yscale("log")
    plt.xlim(0.0,8.0); plt.xticks([0.5*i for i in range(17)])
    plt.grid(True,which="both",alpha=.3); plt.legend(loc="upper right"); plt.tight_layout()
    metric_stem={"decodeTimeMeanNs":"decode_latency","miscorrectionRate":"miscorrection"}.get(metric,metric)
    stem=f"stage10_cfo_formal_k{payload}_{metric_stem}"
    png=PLOTS/f"{stem}.png"; fig=RESULTS/f"stage10_cfo_formal_figure_data_k{payload}_{metric_stem}.csv"
    plt.savefig(png,dpi=300); plt.close()
    with fig.open("w",encoding="utf-8",newline="") as f:
      w=csv.DictWriter(f,fieldnames=figure_rows[0].keys()); w.writeheader(); w.writerows(figure_rows)
    manifest={"stageId":"stage10_cfo_formal","sourceCsv":str(source.relative_to(STAGE)),
      "sourceCsvSha256":hashlib.sha256(source.read_bytes()).hexdigest(),
      "figureData":str(fig.relative_to(STAGE)),"figureDataSha256":hashlib.sha256(fig.read_bytes()).hexdigest(),
      "png":str(png.relative_to(STAGE)),"pngSha256":hashlib.sha256(png.read_bytes()).hexdigest(),
      "xAxis":"SNR","targetSnrGridDb":[0.5*i for i in range(17)],"snrStepDb":0.5,
      "snrMinDb":0.0,"snrMaxDb":8.0,"pointCountPerCase":17,
      "snrFormula":"snrDb=ebn0Db+10*log10(actualRate)",
      "ebn0InverseFormula":"ebn0Db=targetSnrDb-10*log10(actualRate)",
      "stopRule":{"minFrames":1000,"targetFrameErrors":200,"maxFrames":50000},
      "zeroValuePolicy":"raw zero retained; plotValue=0.5/denominator for log display only",
      "caseStyles":{c:{"legendLabel":styles[c][0],"color":styles[c][1],
                      "lineStyle":styles[c][2],"marker":styles[c][3]} for c in styles if c.startswith(f"K{payload}")},
      "generatedFromGitCommit":rows[0]["gitCommit"]}
    (MANIFESTS/f"stage10_cfo_formal_plot_manifest_k{payload}_{metric_stem}.json").write_text(
      json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS_STAGE10_CFO_FORMAL_PLOT")
