import csv
import hashlib
import json
import sys
from pathlib import Path


def require(condition, message):
    if not condition: raise RuntimeError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/"stage15_scientific_plots"
    inventory=list(csv.DictReader((root/"results"/"plot_inventory.csv").open(encoding="utf-8")))
    require(len(inventory)==50,"expected 50 distinct plots")
    require(sum(row["scheme"]=="BCH" for row in inventory)==29 and sum(row["scheme"]=="CC" for row in inventory)==21,"scheme plot counts mismatch")
    baseline_ids={
        "BCH":{"01_methods_fer","02_methods_ber","03_burst_2_fer","04_burst_5_fer","05_burst_10_fer","16_decodeTimeMeanNsWeighted","22_burst_5_ber","23_burst_10_ber"},
        "CC":{"01_methods_fer","02_methods_ber","03_burst_2_fer","04_burst_5_fer","05_burst_10_fer","16_decodeTimeMeanNsWeighted"},
    }
    position_tokens=("six_positions","mean_position","max_position","min_position","position_sensitivity")
    blocked=[]
    for item in inventory:
        directory=Path(item["directory"]); require(directory.is_dir(),"plot directory missing")
        required=["figure.png","figure_data.csv","plot_manifest.json","plot_validation.json","sha256.txt","readme.txt"]
        require(all((directory/name).is_file() for name in required),f"missing plot asset: {directory}")
        require((directory/"figure.png").stat().st_size>1000,"empty PNG")
        manifest=json.loads((directory/"plot_manifest.json").read_text(encoding="utf-8")); validation=json.loads((directory/"plot_validation.json").read_text(encoding="utf-8"))
        require(manifest["smoothingApplied"] is False and not manifest["forbiddenAnnotations"],"forbidden plot transformation/annotation")
        require(all(Path(path).is_file() for path in manifest["sourceAbsolutePaths"]),"source absolute path missing")
        require(Path(manifest["historicalReferenceAbsolutePath"]).is_file() and manifest["historicalReferenceUsedInFigure"] is False,"historical reference rule mismatch")
        rows=list(csv.DictReader((directory/"figure_data.csv").open(encoding="utf-8")))
        expected_baseline=item["plotId"] in baseline_ids[item["scheme"]]
        if expected_baseline:
            require(manifest.get("containsNoBurstBaseline") is True,"applicable plot lacks no-burst baseline")
            require(manifest.get("noBurstBaselineHistorical") is True and manifest.get("noBurstSimulationRerun") is False,"no-burst provenance mismatch")
            require(manifest.get("interpolation") is False and manifest.get("noInterpolation") is True and manifest.get("smoothing") is False and manifest.get("syntheticData") is False,"baseline transformation policy mismatch")
            baseline=[row for row in rows if row.get("channelCondition")=="NO_BURST_AWGN"]
            require(baseline and all(row["sourceType"].startswith("HISTORICAL_FORMAL") and Path(row["sourceCsvAbsolutePath"]).is_file() and row["sourceRowKey"] and row["interpolated"]=="false" for row in baseline),"untraceable no-burst point")
        if any(token in item["plotId"] for token in position_tokens):
            require(not any(row.get("channelCondition")=="NO_BURST_AWGN" for row in rows),"fake no-burst position series")
        for row in rows:
            if manifest["logYAxis"] and row["rawY"]!="" and float(row["rawY"])==0:
                require(row["plotted"]=="false" and row["exclusionReason"]=="ZERO_ON_LOG_AXIS","zero log policy violation")
            require(row["nonMonotonicHighSnrAnomaly"] in ("true","false"),"anomaly flag missing")
        if validation["status"]!="PASS": blocked.append(item["plotId"])
        expected={line.split("  ",1)[1]:line.split("  ",1)[0] for line in (directory/"sha256.txt").read_text(encoding="utf-8").splitlines() if line}
        for name,value in expected.items(): require(digest(directory/name)==value,f"SHA mismatch: {directory/name}")
    require(not blocked,f"blocked plots: {blocked}")
    bch_ids={row["plotId"] for row in inventory if row["scheme"]=="BCH"}
    require("21_all_start_heatmap" not in bch_ids and {"21_all_start_heatmap_2_percent","22_all_start_heatmap_5_percent"}.issubset(bch_ids),"BCH heatmap inventory mismatch")
    archive=root/"archive"/"v02_20260805_before_bch_plot_style_and_heatmap_update"/"bch"
    require((archive/"21_all_start_heatmap").is_dir(),"archived BCH 10% heatmap missing")
    style_ids={"01_methods_fer","02_methods_ber","03_burst_2_fer","04_burst_5_fer","05_burst_10_fer","07_mean_position_fer","08_max_position_fer","09_min_position_fer","11_absoluteFerImprovement","12_relativeFerReductionPercent","22_burst_5_ber","23_burst_10_ber","24_mean_position_ber","25_max_position_ber","26_min_position_ber","27_absoluteBerImprovement","28_relativeBerReductionPercent"}
    expected_styles={"BCH_NONE":("-","o",None),"BCH_CODEBLOCK_D19":("--","o","none"),"BCH_ROW_COLUMN_R15":("-.","s",None),"BCH_GLOBAL_PSEUDO_285":(":","^","none")}
    for plot_id in style_ids:
        directory=root/"results"/"bch"/plot_id
        manifest=json.loads((directory/"plot_manifest.json").read_text(encoding="utf-8")); styles=manifest["configurationStyleMap"]
        for config,(line,marker,face) in expected_styles.items():
            require(config in styles and styles[config]["linestyle"]==line and styles[config]["marker"]==marker and styles[config]["markerfacecolor"]==face,"BCH style mismatch")
        if plot_id in baseline_ids["BCH"]:
            require(styles["NO_BURST_AWGN"]["color"]=="#000000" and styles["NO_BURST_AWGN"]["marker"]=="D" and styles["NO_BURST_AWGN"]["markerfacecolor"]=="none" and styles["NO_BURST_AWGN"]["linewidth"]==2.0,"BCH no-burst style mismatch")
    expected_cc={"NO_BURST_AWGN":("#000000","-","D","none"),"CC_NONE":("#1f77b4","-","o","#1f77b4"),"CC_PSEUDO_128_RECOMMENDED":("#ff7f0e","--","^","none"),"CC_SHORT_D8_RECOMMENDED":("#d62728","-.","s","#d62728"),"CC_SHORT_D16_CONTROL_128":("#2ca02c",":","o","none")}
    for plot_id in baseline_ids["CC"]-{"16_decodeTimeMeanNsWeighted"}:
        styles=json.loads((root/"results"/"cc"/plot_id/"plot_manifest.json").read_text(encoding="utf-8"))["configurationStyleMap"]
        for config,(color,line,marker,face) in expected_cc.items():
            require(config in styles and styles[config]["color"]==color and styles[config]["linestyle"]==line and styles[config]["marker"]==marker and styles[config]["markerfacecolor"]==face,"CC style mismatch")
    for plot_id in {"01_methods_fer","02_methods_ber","04_burst_5_fer","05_burst_10_fer","07_mean_position_fer","08_max_position_fer","09_min_position_fer","11_absoluteFerImprovement","12_relativeFerReductionPercent"}:
        previous=list(csv.DictReader((archive/plot_id/"figure_data.csv").open(encoding="utf-8")))
        current=list(csv.DictReader((root/"results"/"bch"/plot_id/"figure_data.csv").open(encoding="utf-8")))
        current=[r for r in current if r["series"]!="无突发信道（AWGN）"]
        require(sorted((r["series"],float(r["x"]),float(r["rawY"])) for r in previous)==sorted((r["series"],float(r["x"]),float(r["rawY"])) for r in current),"no-burst update changed existing BCH figure data")
    for plot_id,ratio,row_count,start_count in (("21_all_start_heatmap_2_percent",0.02,1120,280),("22_all_start_heatmap_5_percent",0.05,1088,272)):
        directory=root/"results"/"bch"/plot_id; manifest=json.loads((directory/"plot_manifest.json").read_text(encoding="utf-8")); rows=list(csv.DictReader((directory/"figure_data.csv").open(encoding="utf-8")))
        require(len(rows)==row_count and len({int(r["x"]) for r in rows})==start_count,"BCH heatmap start coverage mismatch")
        require(manifest["burstRatioRequested"]==ratio and manifest["colorRange"]==[0,1] and manifest["interpolation"]=="nearest","BCH heatmap metadata mismatch")
    for scheme,plot_ids in baseline_ids.items():
        for plot_id in plot_ids:
            archive_root=root/"results"/scheme.lower()/plot_id/"archive"
            versions=sorted(archive_root.glob("v*_20260811_before_no_burst_baseline_update"))
            require(versions,"no-burst archive missing")
            archived=versions[-1]
            require(all((archived/name).is_file() for name in ("figure.png","figure_data.csv","plot_manifest.json","plot_validation.json","sha256.txt","previous_sha256.txt","previous_readme.txt","readme.txt")),"archive incomplete")
            archive_text=(archived/"readme.txt").read_text(encoding="utf-8")
            require("旧图是否包含无突发基线：否" in archive_text and "数据是否重跑：否" in archive_text,"archive README mismatch")
            archived_hashes={line.split("  ",1)[1]:line.split("  ",1)[0] for line in (archived/"sha256.txt").read_text(encoding="utf-8").splitlines() if line}
            require(all(digest(archived/name)==value for name,value in archived_hashes.items()),"archive SHA mismatch")
    baseline_root=root/"no_burst_baseline"
    audit=list(csv.DictReader((baseline_root/"baseline_source_audit.csv").open(encoding="utf-8")))
    require(any(row["scheme"]=="BCH" and row["matchedToS7"]=="true" and row["usedForPlot"]=="true" for row in audit),"BCH baseline audit missing")
    require(any(row["scheme"]=="CC" and row["matchedToS7"]=="true" and row["usedForPlot"]=="true" for row in audit),"CC baseline audit missing")
    require("复杂度基线明确为 N/A" in (baseline_root/"baseline_source_audit.md").read_text(encoding="utf-8"),"complexity N/A missing")
    frozen=json.loads((baseline_root/"original_input_hashes.json").read_text(encoding="utf-8"))
    require(frozen["noFormalRerun"] is True and all(Path(path).is_file() and digest(Path(path))==value for path,value in frozen["before"].items()),"formal/historical input SHA changed")
    report={"status":"PASS","plotCount":len(inventory),"bchPlotCount":29,"ccPlotCount":21,"noBurstBaselinePlots":sum(len(x) for x in baseline_ids.values()),"archiveComplete":True,"noSyntheticData":True,"noInterpolation":True,"noSmoothing":True,"originalInputsUnchanged":True,"blockedPlots":blocked,"mergeStatus":"NOT_MERGED"}
    (root/"results"/"stage15_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("PASS_S7_STAGE15 plots=50")
    return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE15: {error}",file=sys.stderr); raise
