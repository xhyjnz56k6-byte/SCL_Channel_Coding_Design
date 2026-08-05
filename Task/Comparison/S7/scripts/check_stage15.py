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
    style_ids={"01_methods_fer","02_methods_ber","04_burst_5_fer","05_burst_10_fer","07_mean_position_fer","08_max_position_fer","09_min_position_fer","11_absoluteFerImprovement","12_relativeFerReductionPercent","22_burst_5_ber","23_burst_10_ber","24_mean_position_ber","25_max_position_ber","26_min_position_ber","27_absoluteBerImprovement","28_relativeBerReductionPercent"}
    expected_styles={"BCH_NONE":("-","o",None),"BCH_CODEBLOCK_D19":("--","o","none"),"BCH_ROW_COLUMN_R15":("-.","s",None),"BCH_GLOBAL_PSEUDO_285":(":","^","none")}
    for plot_id in style_ids:
        directory=root/"results"/"bch"/plot_id
        manifest=json.loads((directory/"plot_manifest.json").read_text(encoding="utf-8")); styles=manifest["configurationStyleMap"]
        for config,(line,marker,face) in expected_styles.items():
            require(config in styles and styles[config]["linestyle"]==line and styles[config]["marker"]==marker and styles[config]["markerfacecolor"]==face,"BCH style mismatch")
    for plot_id in {"01_methods_fer","02_methods_ber","04_burst_5_fer","05_burst_10_fer","07_mean_position_fer","08_max_position_fer","09_min_position_fer","11_absoluteFerImprovement","12_relativeFerReductionPercent"}:
        previous=list(csv.DictReader((archive/plot_id/"figure_data.csv").open(encoding="utf-8")))
        current=list(csv.DictReader((root/"results"/"bch"/plot_id/"figure_data.csv").open(encoding="utf-8")))
        require(sorted((r["series"],float(r["x"]),float(r["rawY"])) for r in previous)==sorted((r["series"],float(r["x"]),float(r["rawY"])) for r in current),"style update changed BCH figure data")
    for plot_id,ratio,row_count,start_count in (("21_all_start_heatmap_2_percent",0.02,1120,280),("22_all_start_heatmap_5_percent",0.05,1088,272)):
        directory=root/"results"/"bch"/plot_id; manifest=json.loads((directory/"plot_manifest.json").read_text(encoding="utf-8")); rows=list(csv.DictReader((directory/"figure_data.csv").open(encoding="utf-8")))
        require(len(rows)==row_count and len({int(r["x"]) for r in rows})==start_count,"BCH heatmap start coverage mismatch")
        require(manifest["burstRatioRequested"]==ratio and manifest["colorRange"]==[0,1] and manifest["interpolation"]=="nearest","BCH heatmap metadata mismatch")
    report={"status":"PASS","plotCount":len(inventory),"bchPlotCount":29,"ccPlotCount":21,"blockedPlots":blocked,"mergeStatus":"NOT_MERGED"}
    (root/"results"/"stage15_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("PASS_S7_STAGE15 plots=50")
    return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE15: {error}",file=sys.stderr); raise
