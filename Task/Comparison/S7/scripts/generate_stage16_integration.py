import csv
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def main() -> int:
    formal = {"BCH": ROOT/"stage10_bch_formal"/"results"/"formal_results.csv", "CC": ROOT/"stage11_cc_formal"/"results"/"formal_results.csv"}
    for scheme, path in formal.items():
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        write_csv(ROOT/"results"/scheme.lower()/"formal_result_reference.csv", ["scheme","rowCount","comparisonGroups","sourceAbsolutePath","sourceSha256","configHash","useForFinalConclusion"], [{"scheme":scheme,"rowCount":len(rows),"comparisonGroups":len(rows)//4,"sourceAbsolutePath":str(path.resolve()),"sourceSha256":digest(path),"configHash":rows[0]["configHash"],"useForFinalConclusion":"true"}])

    ldpc_source = ROOT.parents[1]/"Comparison"/"S6"/"results"/"ldpc"/"ldpc_n560_integrated_results.csv"
    ldpc_rows = list(csv.DictReader(ldpc_source.open(encoding="utf-8")))
    fields = list(ldpc_rows[0]) + ["s7ReferenceSourceAbsolutePath","s7ChannelCompatibility","s7UseRestriction"]
    for row in ldpc_rows:
        row.update({"s7ReferenceSourceAbsolutePath":str(ldpc_source.resolve()),"s7ChannelCompatibility":"INCOMPATIBLE_AWGN_ONLY_NO_CONTIGUOUS_POLARITY_REVERSAL","s7UseRestriction":"INDEPENDENT_REFERENCE_TABLE_ONLY_NOT_FOR_INTERLEAVER_RANKING_OR_BURST_TOLERANCE"})
    write_csv(ROOT/"results"/"ldpc_baseline"/"ldpc_baseline_reference.csv", fields, ldpc_rows)

    latency = {row["configurationId"]:row for row in csv.DictReader((ROOT/"stage13_latency_complexity"/"results"/"latency_complexity_summary.csv").open(encoding="utf-8"))}
    tolerance = {row["configurationId"]:row for row in csv.DictReader((ROOT/"stage14_fer_improvement"/"results"/"burst_tolerance_summary.csv").open(encoding="utf-8"))}
    ranking = {row["configurationId"]:row for row in csv.DictReader((ROOT/"stage14_fer_improvement"/"results"/"recommendation_ranking.csv").open(encoding="utf-8"))}
    metric_fields=["scheme","configurationId","comparisonRole","rankAmongInterleavers","meanFormalFer","worstHighWorkpointStartFer","burstToleranceStatus","decodeTimeMeanNsWeighted","additionalCpuTimeMeanNsWeighted","bufferBits","startupDelayBits","startupDelayTrellisSteps","interpretationScope"]
    metrics=[]
    for config,row in sorted(latency.items(),key=lambda item:(item[1]["scheme"],item[0])):
        rank=ranking.get(config,{})
        metrics.append({"scheme":row["scheme"],"configurationId":config,"comparisonRole":row["comparisonRole"],"rankAmongInterleavers":rank.get("rank",""),"meanFormalFer":rank.get("meanFormalFer",""),"worstHighWorkpointStartFer":rank.get("worstHighWorkpointStartFer",""),"burstToleranceStatus":tolerance[config]["burstToleranceStatus"],"decodeTimeMeanNsWeighted":row["decodeTimeMeanNsWeighted"],"additionalCpuTimeMeanNsWeighted":row["additionalCpuTimeMeanNsWeighted"],"bufferBits":row["bufferBits"],"startupDelayBits":row["startupDelayBits"],"startupDelayTrellisSteps":row["startupDelayTrellisSteps"],"interpretationScope":rank.get("interpretationScope","BASELINE_REFERENCE")})
    write_csv(ROOT/"S7_metric_summary.csv",metric_fields,metrics)

    important=[
        ("BCH_FORMAL",formal["BCH"],"FORMAL_PRIMARY"),("CC_FORMAL",formal["CC"],"FORMAL_PRIMARY"),
        ("ALL_START_BCH",ROOT/"stage12_all_start_scan"/"results"/"bch"/"all_start_results.csv","FORMAL_SPECIALTY"),
        ("ALL_START_BCH_2_PERCENT",ROOT/"stage12_all_start_scan"/"results"/"bch_2_percent"/"all_start_results.csv","FORMAL_SPECIALTY_SUPPLEMENT"),
        ("ALL_START_CC",ROOT/"stage12_all_start_scan"/"results"/"cc"/"all_start_results.csv","FORMAL_SPECIALTY"),
        ("LATENCY",ROOT/"stage13_latency_complexity"/"results"/"latency_complexity_summary.csv","DERIVED_VALIDATED"),
        ("RECOMMENDATION",ROOT/"stage14_fer_improvement"/"results"/"recommendation_ranking.csv","DERIVED_VALIDATED"),
        ("PLOTS",ROOT/"stage15_scientific_plots"/"results"/"plot_inventory.csv","DERIVED_VALIDATED"),
        ("LDPC_REFERENCE",ROOT/"results"/"ldpc_baseline"/"ldpc_baseline_reference.csv","INDEPENDENT_INCOMPATIBLE_REFERENCE")]
    inventory=[]
    for name,path,role in important: inventory.append({"resultId":name,"role":role,"absolutePath":str(path.resolve()),"bytes":path.stat().st_size,"sha256":digest(path),"exists":"true"})
    write_csv(ROOT/"S7_result_inventory.csv",["resultId","role","absolutePath","bytes","sha256","exists"],inventory)

    plot_source=ROOT/"stage15_scientific_plots"/"results"/"plot_inventory.csv"
    (ROOT/"S7_plot_inventory.csv").write_text(plot_source.read_text(encoding="utf-8"),encoding="utf-8")
    source_paths=[ROOT/"CMakeLists.txt"]+sorted((ROOT/"current").rglob("*.cpp"))+sorted((ROOT/"current").rglob("*.hpp"))+sorted((ROOT/"current").rglob("*.m"))+sorted((ROOT/"scripts").glob("*.py"))+sorted((ROOT/"configs").glob("*.json"))
    source_rows=[{"relativePath":str(path.relative_to(ROOT)).replace('\\','/'),"absolutePath":str(path.resolve()),"bytes":path.stat().st_size,"sha256":digest(path)} for path in source_paths]
    write_csv(ROOT/"S7_source_inventory.csv",["relativePath","absolutePath","bytes","sha256"],source_rows)

    excluded_roots={ROOT/"build"}
    files=[]
    for path in ROOT.rglob("*"):
        if not path.is_file() or path==ROOT/"S7_sha256.txt": continue
        if any(parent in path.parents or path==parent for parent in excluded_roots): continue
        files.append(path)
    (ROOT/"S7_sha256.txt").write_text("".join(f"{digest(path)}  {str(path.relative_to(ROOT)).replace(os.sep,'/')}\n" for path in sorted(files)),encoding="utf-8")
    print(f"PASS_S7_STAGE16_GENERATION results={len(inventory)} sources={len(source_rows)} hashes={len(files)}")
    return 0


if __name__=="__main__": raise SystemExit(main())
