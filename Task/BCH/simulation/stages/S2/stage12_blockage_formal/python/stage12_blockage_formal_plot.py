import csv,hashlib,json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"];plt.rcParams["axes.unicode_minus"]=False
STAGE=Path(__file__).resolve().parents[1];R=STAGE/"results";P=STAGE/"plots";M=STAGE/"manifests";P.mkdir(exist_ok=True);M.mkdir(exist_ok=True)
source=R/"stage12_blockage_formal_result_summary.csv"
with source.open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f))
styles={"S15":("分块","#0072B2","-","o"),"M255K207":("255整块","#D55E00","--","s"),
"M511K421":("421整块","#009E73","-.","^"),"M511K385":("385整块","#CC79A7",":","D")}
def style(case,payload):
 key=case.split("_",1)[1];label,color,line,marker=styles[key]
 if payload==300 and key=="M255K207":label="255双块"
 return label,color,line,marker
specs=[]
for payload in (200,300):
 for metric,title,ylabel in [("ber","误码率","BER"),("fer","误帧率","FER"),("miscorrectionRate","误纠率","误纠率")]:
  specs.append(("RATIO",payload,metric,f"{payload}比特BCH遮挡{title}",ylabel,"ratio"))
 for metric,title,ylabel in [("ber","误码率","BER"),("fer","误帧率","FER")]:
  specs.append(("SNR",payload,metric,f"{payload}比特BCH遮挡{title}",ylabel,"snr"))
for ex,payload,metric,title,ylabel,xkind in specs:
 figrows=[];plt.figure(figsize=(7.2,4.8))
 for case in [r["caseId"] for r in rows if int(r["payloadLength"])==payload]:
  if any(z["caseId"]==case for z in figrows):continue
  g=[r for r in rows if r["experimentType"]==ex and r["caseId"]==case];g.sort(key=lambda r:float(r["actualBlockageRatio"] if xkind=="ratio" else r["snrDb"]))
  label,color,line,marker=style(case,payload);xs=[float(r["actualBlockageRatio"] if xkind=="ratio" else r["snrDb"]) for r in g];raw=[float(r[metric]) for r in g]
  plot=[v if v>0 else .5/(int(r["totalPayloadBits"]) if metric=="ber" else int(r["totalFrames"])) for v,r in zip(raw,g)]
  plt.plot(xs,plot,label=label,color=color,linestyle=line,marker=marker)
  for r,v,pv in zip(g,raw,plot):figrows.append({"caseId":case,"legendLabel":label,"payloadLength":payload,"encodedLength":r["encodedLength"],
   "actualRate":r["actualRate"],"ebn0Db":r["ebn0Db"],"snrDb":r["snrDb"],"metricName":metric,"metricValue":v,
   "totalFrames":r["totalFrames"],"errorCount":r["payloadErrorBits"] if metric=="ber" else r["payloadErrorFrames"] if metric=="fer" else r["miscorrectionFrames"],
   "isZeroObserved":int(v==0),"plotSurrogateUsed":int(v==0),"plotValue":pv,"requestedBlockageRatio":r["requestedBlockageRatio"],
   "blockageLengthSymbols":r["blockageLengthSymbols"],"actualBlockageRatio":r["actualBlockageRatio"]})
 plt.xlabel("遮挡比例" if xkind=="ratio" else "SNR");plt.ylabel(ylabel);plt.title(title);plt.yscale("log");plt.grid(True,which="both",alpha=.3);plt.legend(loc="upper right")
 if xkind=="ratio":plt.gca().xaxis.set_major_formatter(PercentFormatter(1.0))
 plt.tight_layout();metric_stem="miscorrection" if metric=="miscorrectionRate" else metric
 stem=f"stage12_blockage_formal_k{payload}_{metric_stem}_{'vs_ratio' if xkind=='ratio' else 'vs_snr'}"
 png=P/f"{stem}.png";data=R/f"stage12_blockage_formal_figure_data_k{payload}_{metric_stem}_{'vs_ratio' if xkind=='ratio' else 'vs_snr'}.csv";plt.savefig(png,dpi=300);plt.close()
 with data.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=figrows[0]);w.writeheader();w.writerows(figrows)
 manifest={"stageId":"stage12_blockage_formal","sourceCsv":str(source.relative_to(STAGE)),"sourceCsvSha256":hashlib.sha256(source.read_bytes()).hexdigest(),
  "figureData":str(data.relative_to(STAGE)),"figureDataSha256":hashlib.sha256(data.read_bytes()).hexdigest(),"png":str(png.relative_to(STAGE)),
  "pngSha256":hashlib.sha256(png.read_bytes()).hexdigest(),"xAxis":"遮挡比例" if xkind=="ratio" else "SNR",
  "snrFormula":"snrDb=ebn0Db+10*log10(actualRate)","zeroValuePolicy":"raw zero retained; plotValue=0.5/denominator only"}
 (M/f"stage12_blockage_formal_plot_manifest_k{payload}_{metric_stem}_{'vs_ratio' if xkind=='ratio' else 'vs_snr'}.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS_STAGE12_BLOCKAGE_FORMAL_PLOT")
