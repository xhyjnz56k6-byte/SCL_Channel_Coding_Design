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
    require(len(inventory)==42,"expected 42 distinct plots")
    require(sum(row["scheme"]=="BCH" for row in inventory)==21 and sum(row["scheme"]=="CC" for row in inventory)==21,"scheme plot counts mismatch")
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
    report={"status":"PASS","plotCount":len(inventory),"bchPlotCount":21,"ccPlotCount":21,"blockedPlots":blocked,"mergeStatus":"NOT_MERGED"}
    (root/"results"/"stage15_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("PASS_S7_STAGE15 plots=42")
    return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE15: {error}",file=sys.stderr); raise
