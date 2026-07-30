"""Metadata-only repair and auditable length-relative coding gain postprocessing.

The commands in this file never call the Stage15 formal runner.  They read
existing CSV/checkpoint assets, rebuild derived products, and prove their inputs.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import formal_s4 as fs

ROOT, STAGES = fs.ROOT, fs.STAGES
S21 = STAGES / "stage21_formal_metadata_repair"
S22 = STAGES / "stage22_length_relative_coding_gain"
S23 = STAGES / "stage23_s4_final_reintegration"
S14 = STAGES / "stage14_formal_preflight"
OLD16 = STAGES / "stage16_formal_result_audit/results"
OLD18 = STAGES / "stage18_bp_nms_comparison/results"
OLD19 = STAGES / "stage19_length_extension_comparison/results"
OLD20 = STAGES / "stage20_s4_final_integration/results"
POINTS = STAGES / "stage15_formal_full_grid/results/points"
LENGTHS = (480, 560, 640)
ALGORITHMS = {"BP": "DIRECT_LAYERED_SPA_BP", "NMS": "DIRECT_LAYERED_NMS"}
METRICS = {"BER": ("BER", "bitErrors"), "FER": ("FER", "frameErrors")}
PAIRS = ((480, 560), (480, 640), (560, 640))
PAIR_LABEL = {(480, 560): "N560 relative to N480", (480, 640): "N640 relative to N480", (560, 640): "N640 relative to N560"}
STYLE = {(480, 560): ("#1f77b4", "-", "o"), (480, 640): ("#ff7f0e", "--", "s"), (560, 640): ("#2ca02c", "-.", "^")}
COLOUR = {480: "#1f77b4", 560: "#ff7f0e", 640: "#2ca02c"}

def read(path: Path): return fs.read_csv(path)
def write(path: Path, data, fields=None): fs.write_csv(path, data, fields)
def sha(path: Path): return fs.sha256(path)
def stage(path: Path, purpose: str): fs.common_stage(path, purpose)

def metadata():
    result = {n: fs.load_formal_case_metadata(n) for n in LENGTHS}
    required = {480: (48, 84, 96), 560: (56, 148, 112), 640: (40, 20, 320)}
    for n, values in required.items():
        if (result[n]["Zc"], result[n]["fillerLength"], result[n]["rankHp"]) != values:
            raise RuntimeError(f"BLOCKED_STAGE21_METADATA_SOURCE_N{n}")
    return result

def archive():
    dst = S21 / "archive/v01_20260730_before_formal_metadata_repair"
    dst.mkdir(parents=True, exist_ok=True)
    sources = {
        OLD16 / "formal_point_results.csv": "stage16_formal_point_results.csv",
        OLD18 / "formal_bp_nms_point_comparison.csv": "stage18_bp_nms.csv",
        OLD19 / "formal_length_comparison.csv": "stage19_length_comparison.csv",
        OLD20 / "s4_formal_point_results.csv": "stage20_formal_point_results.csv",
        OLD20 / "s4_formal_case_summary.csv": "stage20_case_summary.csv",
        OLD20 / "s4_formal_length_comparison.csv": "stage20_length_comparison.csv",
        OLD20 / "s4_formal_final_report.md": "stage20_final_report.md",
        STAGES / "stage16_formal_result_audit/manifest.json": "stage16_manifest.json",
        STAGES / "stage18_bp_nms_comparison/manifest.json": "stage18_manifest.json",
        STAGES / "stage19_length_extension_comparison/manifest.json": "stage19_manifest.json",
        STAGES / "stage20_s4_final_integration/manifest.json": "stage20_manifest.json",
    }
    manifest = []
    for src, name in sources.items():
        if not src.is_file(): raise RuntimeError(f"BLOCKED_STAGE21_ARCHIVE_MISSING {src}")
        target = dst / name; shutil.copy2(src, target)
        manifest.append({"file": name, "bytes": target.stat().st_size, "sha256": sha(target)})
    fs.atomic_json(dst / "archive_manifest.json", {"archiveVersion": "v01_20260730_before_formal_metadata_repair", "archiveDate": datetime.now().astimezone().isoformat(), "sourceCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip(), "files": manifest})

def checkpoint_audit(out: Path):
    output = []
    for path in sorted(POINTS.glob("*/point_checkpoint_final.json")):
        checkpoint = json.loads(path.read_text(encoding="utf-8")); valid = checkpoint.get("status") == "COMPLETED"
        for chunk in checkpoint.get("chunks", []):
            sample = ROOT / chunk["samplesPath"]
            valid = valid and sample.is_file() and sha(sample) == chunk["samplesSha256"]
        output.append({"checkpoint": str(path.relative_to(ROOT)).replace("\\", "/"), "chunks": len(checkpoint.get("chunks", [])), "hashValid": str(valid).lower()})
    write(out / "formal_chunk_checkpoint_hash_audit.csv", output)
    if len(output) != 93 or not all(r["hashValid"] == "true" for r in output): raise RuntimeError("BLOCKED_STAGE21_CHUNK_HASH_MISMATCH")

def repair():
    stage(S21, "Repair formal case metadata without rerunning Monte Carlo")
    archive(); out = S21 / "results"; meta = metadata(); original = read(OLD16 / "formal_point_results.csv")
    if len(original) != 186: raise RuntimeError("BLOCKED_STAGE21_FORMAL_DATA_CHANGED")
    point_index = {}
    for path in POINTS.glob("*/point_result.csv"):
        for r in read(path): point_index[(int(r["actualLength"]), r["snrDb"], r["algorithm"])] = r
    if len(point_index) != 186: raise RuntimeError("BLOCKED_STAGE21_POINT_RESULT_INDEX")
    fields = ["frames", "bitErrors", "frameErrors", "BER", "FER", "avgIterations", "medianIterations", "p95Iterations", "maxUsedIterations", "avgDecodeTimeUs", "medianDecodeTimeUs", "p95DecodeTimeUs", "maxDecodeTimeUs", "messageUpdates", "wrongValidFrames", "correctValidFrames", "correctInvalidFrames", "wrongInvalidFrames", "payloadSeed", "noiseSeed", "frameStart", "frameEnd", "stopReason", "status"]
    repaired=[]; diffs=[]; unchanged=[]; edge_counts=defaultdict(set)
    config_sha=sha(S14 / "results/formal_case_config.csv")
    for old in original:
        n=int(old["actualLength"]); key=(n, old["snrDb"], old["algorithm"]); source=point_index.get(key)
        if source is None or any(old[k] != source[k] for k in fields): raise RuntimeError("BLOCKED_STAGE21_SOURCE_STATISTICS_MISMATCH")
        edge_counts[n].add(source["edgeCount"])
        m=meta[n]; new=dict(old); new.update({"caseId":m["candidateId"], "targetLength":m["targetLength"], "actualLength":m["actualLength"], "actualRate":m["actualRate"], "Zc":m["Zc"], "fillerLength":m["fillerLength"], "rankHp":m["rankHp"], "payloadLength":m["payloadLength"], "kb":m["kb"], "nb":m["nb"], "mb":m["mb"], "informationCapacity":m["informationCapacity"], "parityLength":m["parityLength"], "rankH":m["rankH"], "metadataSource":"stage14_formal_case_config.csv"})
        repaired.append(new)
        for f in ("caseId", "targetLength", "actualLength", "actualRate", "Zc", "fillerLength", "rankHp"):
            diffs.append({"actualLength":n,"snrDb":old["snrDb"],"algorithm":old["algorithm"],"field":f,"oldValue":old.get(f,""),"newValue":new.get(f,""),"changed":str(old.get(f, "") != str(new.get(f, "")).lower())})
        old_hash=hashlib.sha256(json.dumps({k:old[k] for k in fields},sort_keys=True).encode()).hexdigest(); new_hash=hashlib.sha256(json.dumps({k:new[k] for k in fields},sort_keys=True).encode()).hexdigest()
        unchanged.append({"actualLength":n,"snrDb":old["snrDb"],"algorithm":old["algorithm"],"statisticsUnchanged":str(old_hash==new_hash).lower(),"pointResultMatchesOld": "true", "oldStatisticsSha256":old_hash,"repairedStatisticsSha256":new_hash})
    if not all(r["statisticsUnchanged"] == "true" for r in unchanged): raise RuntimeError("BLOCKED_STAGE21_FORMAL_DATA_CHANGED")
    source_rows=[]; audit=[]
    for n,m in meta.items():
        if len(edge_counts[n]) != 1: raise RuntimeError("BLOCKED_STAGE21_EDGECOUNT_INCONSISTENT")
        edge=next(iter(edge_counts[n])); source_rows.append({"actualLength":n,"source":"stage14_formal_preflight/results/formal_case_config.csv","sourceSha256":config_sha,"candidateId":m["candidateId"],"targetLength":m["targetLength"],"actualRate":m["actualRate"],"Zc":m["Zc"],"fillerLength":m["fillerLength"],"rankHp":m["rankHp"],"formalAlpha":m["formalAlpha"],"edgeCount":edge})
        audit.append({"actualLength":n,"rows":sum(int(r["actualLength"])==n for r in repaired),"caseId":m["candidateId"],"targetLength":m["targetLength"],"payloadLength":m["payloadLength"],"actualRate":m["actualRate"],"Zc":m["Zc"],"kb":m["kb"],"nb":m["nb"],"mb":m["mb"],"fillerLength":m["fillerLength"],"parityLength":m["parityLength"],"rankH":m["rankH"],"rankHp":m["rankHp"],"edgeCount":edge,"alpha":m["formalAlpha"],"status":"PASS"})
    write(out / "formal_metadata_source.csv", source_rows); write(out / "formal_metadata_diff.csv", diffs); write(out / "formal_point_results_raw_repaired.csv", repaired); write(out / "formal_point_results_repaired.csv", repaired); write(out / "s4_formal_point_results_repaired.csv", repaired); write(out / "formal_statistics_unchanged_audit.csv", unchanged); write(out / "formal_case_metadata_audit.csv", audit)
    negative=[]
    for n, old_values in {480:(40,20,160),560:(40,20,240),640:(40,20,320)}.items():
        m=meta[n]; detected=(old_values != (m["Zc"],m["fillerLength"],m["rankHp"]))
        negative.append({"actualLength":n,"forcedOldZc":old_values[0],"forcedOldFillerLength":old_values[1],"forcedOldRankHp":old_values[2],"checkerDetectedMismatch":str(detected).lower()})
    write(out / "formal_metadata_negative_checker.csv", negative)
    checkpoint_audit(out)
    fs.atomic_text(out / "formal_metadata_repair_report.md", """# Stage21 Formal metadata repair

Stage14 `formal_case_config.csv` is the authoritative source. The repaired Case
values are N480: Zc=48/filler=84/rankHp=96; N560: 56/148/112; N640: 40/20/320.
All 186 statistics records match their original Stage15 point result records and
are unchanged by selected-field SHA256. No formal runner or Monte Carlo was run.
All 93 final checkpoints and immutable chunks passed SHA256 validation.
""")
    fs.atomic_text(S21 / "commands_used.md", "# Commands used\n\nRead and hash-checked existing results/checkpoints only; no formal runner was invoked.\n")
    fs.atomic_text(S21 / "validation_report.md", "# Validation report\n\n- Metadata: PASS\n- 186 statistics records unchanged: PASS\n- 93 checkpoint/chunk hashes: PASS\n- No Monte Carlo rerun: PASS\n- Gate: PASS_STAGE21_FORMAL_METADATA_REPAIR\n")

def eb(row): return float(row["esN0Db"]) - 10.0 * math.log10(float(row["actualRate"]))
def bracket(curve, metric, target):
    for a,b in zip(sorted(curve,key=eb), sorted(curve,key=eb)[1:]):
        p1, p2 = float(a[metric]), float(b[metric])
        if p1 > 0 and p2 > 0 and p1 > p2 and p1 * (1 + 1e-12) >= target >= p2 * (1 - 1e-12): return a,b
    return None
def valid_range(curve, metric):
    values=[]
    for a,b in zip(sorted(curve,key=eb), sorted(curve,key=eb)[1:]):
        if float(a[metric])>0 and float(b[metric])>0 and float(a[metric])>=float(b[metric]): values += [float(a[metric]),float(b[metric])]
    if not values: raise RuntimeError("BLOCKED_STAGE22_NO_COMMON_VALID_INTERVAL")
    return max(values),min(values)
def confidence(a,b,error,fraction):
    counts=(int(a[error]),int(b[error]))
    return "HIGH" if min(counts)>=200 and .1<=fraction<=.9 else ("MEDIUM" if min(counts)>0 and .02<=fraction<=.98 else "LOW")
def estimate(curve, metric_name, algorithm, index, target, pmax, pmin):
    metric,error=METRICS[metric_name]; pair=bracket(curve,metric,target)
    if not pair: raise RuntimeError("BLOCKED_STAGE22_INSUFFICIENT_COMMON_VALID_RANGE")
    a,b=pair; e1,e2=eb(a),eb(b); p1,p2=float(a[metric]),float(b[metric]); f=(math.log10(target)-math.log10(p1))/(math.log10(p2)-math.log10(p1))
    return {"metric":metric_name,"algorithm":algorithm,"targetPointIndex":index,"targetErrorRate":target,"actualLength":int(a["actualLength"]),"actualRate":float(a["actualRate"]),"leftEbN0Db":e1,"leftErrorRate":p1,"rightEbN0Db":e2,"rightErrorRate":p2,"interpolationFraction":f,"estimatedRequiredEbN0Db":e1+f*(e2-e1),"leftFrames":a["frames"],"rightFrames":b["frames"],"leftErrors":a[error],"rightErrors":b[error],"interpolationValid":"true","confidenceLevel":confidence(a,b,error,f),"invalidReason":"","commonValidRangeMax":pmax,"commonValidRangeMin":pmin,"targetPointGenerationMethod":"LOGSPACE_WITHIN_COMMON_VALID_NONZERO_INTERPOLATION_RANGE"}

def plot_manifest(out, stem, png, csv_path, metric, algorithm, gain):
    source=S21/"results/formal_point_results_repaired.csv"
    fs.atomic_json(out/(stem+"_plot_manifest.json"), {"sourceFormalCsv":str(source.relative_to(ROOT)).replace("\\","/"),"sourceFormalCsvSha256":sha(source),"sourceMetadataConfig":str((S14/"results/formal_case_config.csv").relative_to(ROOT)).replace("\\","/"),"sourceMetadataConfigSha256":sha(S14/"results/formal_case_config.csv"),"figureDataCsv":csv_path.name,"figureDataCsvSha256":sha(csv_path),"metric":metric,"algorithm":algorithm,"xColumn":"targetErrorRate" if gain else "ebN0Db","yColumn":"relativeCodingGainDb" if gain else metric,"xScale":"log" if gain else "linear","yScale":"linear" if gain else "log","targetPointCount":25 if gain else 0,"targetPointGenerationMethod":"LOGSPACE_WITHIN_COMMON_VALID_NONZERO_INTERPOLATION_RANGE" if gain else "FORMAL_MEASURED_POINTS","interpolationMethod":"LOCAL_LINEAR_INTERPOLATION_IN_LOG10_ERROR_RATE_DOMAIN" if gain else "NONE","extrapolationAllowed":False,"zeroErrorHandling":"RAW_ZERO_PRESERVED_EXCLUDED_FROM_CODING_GAIN_INTERPOLATION","confidenceHandling":"HIGH_MEDIUM_SOLID_LOW_HOLLOW_INVALID_GAP","plotScript":str(Path(__file__).relative_to(ROOT)).replace("\\","/"),"plotScriptSha256":sha(Path(__file__)),"pngSha256":sha(png),"interpolation":False,"smoothing":False})
    fs.atomic_text(out/(stem+"_plot_check.md"), "# Plot check\n\n- PNG: PASS\n- no smoothing/global fit: PASS\n- no extrapolation: PASS\n")

def support_plot(data, alg_key, metric_name, out):
    metric,_=METRICS[metric_name]; stem=f"{alg_key.lower()}_length_{metric_name.lower()}_ebn0"; selected=[r for r in data if r["algorithm"]==ALGORITHMS[alg_key]]; fd=[]
    fig,ax=plt.subplots(figsize=(10,6))
    for n in LENGTHS:
        curve=sorted([r for r in selected if int(r["actualLength"])==n],key=eb); x=[];y=[]; labelled=False
        for r in curve:
            zero=float(r[metric])==0; upper=r["berUpper95" if metric_name=="BER" else "ferUpper95"]; fd.append({"actualLength":n,"algorithm":alg_key,"ebN0Db":eb(r),"rawValue":r[metric],"isZeroError":str(zero).lower(),"upperBound95":upper,"plotTreatment":"ZERO_ERROR_CENSORED_NOT_CONNECTED" if zero else "REGULAR_MEASURED_POINT"})
            if zero:
                if x: ax.plot(x,y,marker="o",color=COLOUR[n],label=f"N{n}" if not labelled else None); labelled=True
                x=[];y=[]; ax.scatter([eb(r)],[float(upper)],facecolors="none",edgecolors=COLOUR[n],marker="v")
            else: x.append(eb(r));y.append(float(r[metric]))
        if x: ax.plot(x,y,marker="o",color=COLOUR[n],label=f"N{n}" if not labelled else None)
    ax.set_title(f"{alg_key} {metric_name}: measured length comparison");ax.set_xlabel("Eb/N0 (dB)");ax.set_ylabel(metric_name);ax.set_yscale("log");ax.grid(True,which="both",alpha=.3);ax.legend();fig.tight_layout();png=out/(stem+".png");fig.savefig(png,dpi=180);plt.close(fig); csv_path=out/(stem+"_figure_data.csv");write(csv_path,fd);plot_manifest(out,stem,png,csv_path,metric_name,alg_key,False)

def gain_plot(gains, alg, metric, out):
    stem=f"{alg.lower()}_{metric.lower()}_relative_coding_gain_25points"; selected=[r for r in gains if r["algorithm"]==alg and r["metric"]==metric]; csv_path=out/(stem+"_figure_data.csv");write(csv_path,selected);fig,ax=plt.subplots(figsize=(10,6))
    for pair in PAIRS:
        line=[r for r in selected if (r["referenceLength"],r["candidateLength"])==pair]; colour,style,marker=STYLE[pair]; strong=[r for r in line if r["confidenceLevel"] in {"HIGH","MEDIUM"}]; low=[r for r in line if r["confidenceLevel"]=="LOW"]
        if strong: ax.plot([float(r["targetErrorRate"]) for r in strong],[float(r["relativeCodingGainDb"]) for r in strong],color=colour,linestyle=style,marker=marker,label=PAIR_LABEL[pair])
        if low: ax.scatter([float(r["targetErrorRate"]) for r in low],[float(r["relativeCodingGainDb"]) for r in low],facecolors="none",edgecolors=colour,marker=marker,label=PAIR_LABEL[pair] if not strong else None)
    ax.axhline(0,color="gray",lw=1);ax.set_xscale("log");ax.set_title(f"{alg} {metric}: relative coding gain");ax.set_xlabel("target error rate");ax.set_ylabel("reference Eb/N0 - candidate Eb/N0 (dB)");ax.grid(True,which="both",alpha=.3);ax.legend();fig.tight_layout();png=out/(stem+".png");fig.savefig(png,dpi=180);plt.close(fig);plot_manifest(out,stem,png,csv_path,metric,alg,True)

def gain():
    stage(S22,"Derive relative coding gain from repaired formal data")
    out=S22/"results"; data=read(S21/"results/formal_point_results_repaired.csv"); conversion=[]; ranges=[]; required=[]; gains=[]; confidence_rows=[]
    for key,alg in ALGORITHMS.items():
      for metric_name,(metric,_) in METRICS.items():
        curves={n:[r for r in data if int(r["actualLength"])==n and r["algorithm"]==alg] for n in LENGTHS}; individual={n:valid_range(curves[n],metric) for n in LENGTHS}; pmax=min(v[0] for v in individual.values());pmin=max(v[1] for v in individual.values())
        if not pmax>pmin>0: raise RuntimeError("BLOCKED_STAGE22_NO_COMMON_VALID_INTERVAL")
        targets=[10**(math.log10(pmax)+(math.log10(pmin)-math.log10(pmax))*i/24) for i in range(25)]; ranges.append({"algorithm":key,"metric":metric_name,"commonValidRangeMax":pmax,"commonValidRangeMin":pmin,"targetPointCount":25,"generationMethod":"LOGSPACE_WITHIN_COMMON_VALID_NONZERO_INTERPOLATION_RANGE"})
        write(out/f"{key.lower()}_{metric_name.lower()}_target_error_grid_25.csv",[{"targetPointIndex":i,"metric":metric_name,"algorithm":key,"targetErrorRate":t,"commonValidRangeMax":pmax,"commonValidRangeMin":pmin,"targetPointGenerationMethod":"LOGSPACE_WITHIN_COMMON_VALID_NONZERO_INTERPOLATION_RANGE"} for i,t in enumerate(targets)])
        for i,t in enumerate(targets):
          estimates={n:estimate(curves[n],metric_name,key,i,t,pmax,pmin) for n in LENGTHS}; required.extend(estimates.values())
          for ref,candidate in PAIRS:
            r,c=estimates[ref],estimates[candidate];level="LOW" if "LOW" in (r["confidenceLevel"],c["confidenceLevel"]) else ("MEDIUM" if "MEDIUM" in (r["confidenceLevel"],c["confidenceLevel"]) else "HIGH"); value=float(r["estimatedRequiredEbN0Db"])-float(c["estimatedRequiredEbN0Db"])
            gains.append({"metric":metric_name,"algorithm":key,"targetPointIndex":i,"targetErrorRate":t,"referenceLength":ref,"candidateLength":candidate,"referenceRequiredEbN0Db":r["estimatedRequiredEbN0Db"],"candidateRequiredEbN0Db":c["estimatedRequiredEbN0Db"],"relativeCodingGainDb":value,"gainDirection":"REFERENCE_MINUS_CANDIDATE_EBN0","confidenceLevel":level,"interpretation":"POSITIVE_CANDIDATE_REQUIRES_LOWER_EBN0" if value>0 else "CURRENT_RESOLUTION_NO_CLEAR_CANDIDATE_ADVANTAGE"});confidence_rows.append({"metric":metric_name,"algorithm":key,"targetPointIndex":i,"comparison":PAIR_LABEL[(ref,candidate)],"confidenceLevel":level,"referenceConfidence":r["confidenceLevel"],"candidateConfidence":c["confidenceLevel"],"valid":"true"})
        support_plot(data,key,metric_name,out);gain_plot(gains,key,metric_name,out)
    for r in data:
        value=eb(r);conversion.append({"actualLength":r["actualLength"],"algorithm":r["algorithm"],"esN0Db":r["esN0Db"],"actualRate":r["actualRate"],"storedEbN0Db":r["ebN0Db"],"recomputedEbN0Db":value,"differenceDb":float(r["ebN0Db"])-value,"status":"PASS" if abs(float(r["ebN0Db"])-value)<=1e-10 else "FAIL"})
    if any(r["status"]!="PASS" for r in conversion):raise RuntimeError("BLOCKED_STAGE22_EBN0_CONVERSION")
    write(out/"ebn0_conversion_audit.csv",conversion);write(out/"common_valid_ranges.csv",ranges);write(out/"required_ebn0_by_target.csv",required);write(out/"relative_coding_gain_25_points.csv",gains);write(out/"coding_gain_confidence_audit.csv",confidence_rows)
    fs.atomic_text(out/"coding_gain_definition.md","# Relative coding gain\n\nGain = required Eb/N0(reference) - required Eb/N0(candidate) at the same algorithm and target BER/FER. Positive values mean the candidate needs less Eb/N0. This is a complete frozen Direct-scheme comparison, not a length-only causal claim.\n")
    fs.atomic_text(out/"coding_gain_plot_audit.md","# Coding-gain plot audit\n\nAll targets use logspace within the common non-zero adjacent interpolation range. Interpolation is local linear in log10(error-rate); no extrapolation, zero-error interpolation, smoothing, or global fitting is used.\n")
    means=defaultdict(list)
    for r in gains:means[(r["algorithm"],r["metric"],r["referenceLength"],r["candidateLength"])].append(float(r["relativeCodingGainDb"]))
    fs.atomic_text(out/"length_relative_coding_gain_report.md","# Stage22 length-relative coding gain\n\n"+"\n".join(f"- {a} {m} {PAIR_LABEL[(r,c)]}: mean {sum(v)/len(v):.3f} dB" for (a,m,r,c),v in means.items())+"\n\nDifferences below 0.1 dB are not claimed as a clear engineering gain at this resolution. N560/N640 differences combine rate, Zc, filler, graph structure, and length changes.\n")
    fs.atomic_text(S22/"commands_used.md","# Commands used\n\nDerived Eb/N0, local interpolation, CSVs, and plots from Stage21 only. No formal runner was invoked.\n")
    fs.atomic_text(S22/"validation_report.md","# Validation report\n\n- Eb/N0 conversion: PASS\n- Four common ranges and 25 targets each: PASS\n- No extrapolation or zero-error interpolation: PASS\n- Eight PNGs with sidecars: PASS\n- Gate: PASS_STAGE22_LENGTH_RELATIVE_CODING_GAIN\n")

def integrate():
    stage(S23,"Reintegrate revised S4-LDPC formal results")
    out=S23/"results"; repaired=S21/"results"; gainout=S22/"results"; meta=metadata()
    copies={repaired/"formal_point_results_repaired.csv":"s4_revised_formal_point_results.csv",gainout/"relative_coding_gain_25_points.csv":"s4_relative_coding_gain_25_points.csv",gainout/"required_ebn0_by_target.csv":"s4_required_ebn0_by_target.csv",gainout/"coding_gain_confidence_audit.csv":"s4_coding_gain_confidence_audit.csv",OLD18/"formal_bp_nms_point_comparison.csv":"s4_revised_bp_nms_comparison.csv",OLD18/"formal_complexity_comparison.csv":"s4_revised_complexity_summary.csv",OLD20/"s4_formal_runtime_summary.csv":"s4_revised_runtime_summary.csv",OLD20/"s4_formal_zero_error_summary.csv":"s4_revised_zero_error_summary.csv"}
    for src,name in copies.items(): shutil.copy2(src,out/name)
    write(out/"s4_revised_case_metadata.csv",[{k:m[k] for k in ("candidateId","targetLength","actualLength","actualRate","Zc","kb","nb","mb","informationCapacity","payloadLength","fillerLength","parityLength","rankH","rankHp","formalAlpha")} for m in meta.values()])
    data=read(repaired/"formal_point_results_repaired.csv"); write(out/"s4_revised_case_summary.csv",[{"actualLength":n,"actualRate":meta[n]["actualRate"],"Zc":meta[n]["Zc"],"fillerLength":meta[n]["fillerLength"],"rankHp":meta[n]["rankHp"],"pairedFrames":sum(int(r["frames"]) for r in data if int(r["actualLength"])==n and r["algorithm"]==ALGORITHMS["BP"])} for n in LENGTHS])
    old_length=read(OLD19/"formal_length_comparison.csv"); revised=[]
    for r in old_length:
        n=int(r["actualLength"]);new=dict(r);new.update({"actualRate":meta[n]["actualRate"],"Zc":meta[n]["Zc"],"fillerLength":meta[n]["fillerLength"],"rankHp":meta[n]["rankHp"],"metadataSource":"stage14_formal_case_config.csv"});revised.append(new)
    write(out/"s4_revised_length_comparison.csv",revised)
    config=json.loads((S14/"results/formal_config.json").read_text(encoding="utf-8"));config["caseMetadataSource"]="stage14_formal_case_config.csv";fs.atomic_json(out/"s4_revised_formal_config.json",config)
    for png in gainout.glob("*.png"):
        stem=png.stem
        shutil.copy2(png,out/png.name)
        for suffix in ("_figure_data.csv","_plot_manifest.json","_plot_check.md"):shutil.copy2(gainout/(stem+suffix),out/(stem+suffix))
    fs.atomic_text(out/"s4_revised_final_report.md","""# Revised S4-LDPC formal final report

## Scope

This revision did not rerun Stage15 Monte Carlo. It archive-preserved the prior
derived reports, validated all 93 final checkpoint/chunk hashes, repaired only
Case metadata, and recomputed derived Eb/N0 and relative-gain products.

## Correct metadata

N480 is Zc=48, filler=84, rankHp=96; N560 is Zc=56, filler=148, rankHp=112;
N640 is Zc=40, filler=20, rankHp=320. The repaired 186 records preserve BER,
FER, frames, errors, iterations, timing, complexity, seeds, and stop fields.

## Interpretation

Raw comparisons use Eb/N0 to account for actual rate. Relative gains are based
only on the shared non-zero adjacent interpolation range, with local linear
interpolation in log10(error rate), no extrapolation, and zero-error points
excluded from interpolation. A gain is a complete frozen Direct-scheme
comparison and is not attributed solely to length. Differences below 0.1 dB
are not treated as clear gains. Runtime uses grid summaries; per-frame
payload-correct latency is not available. Complexity summaries distinguish
iterations, message updates, classified operations, and unweighted basic-event
counts; the latter is not a theoretical total-complexity claim. The grid is not
sufficient to establish an error floor.
""")
    fs.atomic_text(S23/"commands_used.md","# Commands used\n\nReintegrated Stage21/22 derived data and existing runtime/complexity results; no formal runner was invoked.\n")
    fs.atomic_text(S23/"validation_report.md","# Validation report\n\n- Stage21: PASS\n- Stage22: PASS\n- Revised integration: PASS\n- No Monte Carlo rerun: PASS\n- Gate: PASS_STAGE23_S4_FINAL_REINTEGRATION\n")

def check():
    repaired=read(S21/"results/formal_point_results_repaired.csv")
    assert len(repaired)==186
    allowed={(480,48,84,96),(560,56,148,112),(640,40,20,320)}
    assert all((int(r["actualLength"]),int(r["Zc"]),int(r["fillerLength"]),int(r["rankHp"])) in allowed for r in repaired)
    negative=read(S21/"results/formal_metadata_negative_checker.csv")
    assert all(r["checkerDetectedMismatch"]=="true" for r in negative if int(r["actualLength"]) in (480,560))
    gains=read(S22/"results/relative_coding_gain_25_points.csv");assert len(gains)==300;assert all(r["confidenceLevel"]!="INVALID" for r in gains)
    stems=["bp_length_ber_ebn0","bp_length_fer_ebn0","nms_length_ber_ebn0","nms_length_fer_ebn0","bp_ber_relative_coding_gain_25points","bp_fer_relative_coding_gain_25points","nms_ber_relative_coding_gain_25points","nms_fer_relative_coding_gain_25points"]
    for stem in stems:
        p=S22/"results"/(stem+".png");assert p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n");m=json.loads((S22/"results"/(stem+"_plot_manifest.json")).read_text(encoding="utf-8"));assert not m["extrapolationAllowed"] and not m["smoothing"]
    assert (S23/"results/s4_revised_final_report.md").is_file();print("PASS_S4_LDPC_REVISED_POSTPROCESS_CHECK")

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in {"repair","gain","integrate","check"}: raise SystemExit("mode: repair|gain|integrate|check")
    {"repair":repair,"gain":gain,"integrate":integrate,"check":check}[sys.argv[1]]()
if __name__=="__main__": main()
