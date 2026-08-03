#!/usr/bin/env python3
import csv
import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
S5 = ROOT / "Task" / "Comparison" / "S5"
FORMAL = S5 / "results" / "formal" / "merged" / "formal_merged_results.csv"
EXPECTED = "dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947"
STAGE12 = S5 / "stages" / "stage12_known_erasure_cc_validation"
STAGE11_RESULTS = S5 / "results" / "stage11"
AGGREGATE = S5 / "results" / "Aggregate"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    checks = {}
    checks["formalHashUnchanged"] = sha256(FORMAL) == EXPECTED
    stage12_gate = load(STAGE12 / "cpp" / "results" / "cpp_erasure_fraction_gate.json")
    checks["stage12Pass"] = stage12_gate["gate"] == "PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION"
    plot_summary = load(STAGE11_RESULTS / "plot_audit_summary.json")
    checks["chineseReplotCount"] = plot_summary["figureCount"] == 86 and plot_summary["passedFigures"] == 86
    checks["chineseReplotSource"] = plot_summary["sourceFormalCsvSha256"] == EXPECTED
    plot_dirs = [p for p in (STAGE11_RESULTS / "plots").iterdir() if p.is_dir()]
    checks["chinesePlotSidecars"] = len(plot_dirs) == 86 and all(
        all((p / name).exists() for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_check.md", "sha256.txt"))
        for p in plot_dirs)
    checks["chineseFontAndLanguage"] = all(
        (lambda m: m.get("language") == "zh-CN" and m.get("chineseFont") in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"))(load(p / "plot_manifest.json"))
        for p in plot_dirs)
    archives = list((STAGE11_RESULTS / "archive").glob("v??_20260803_before_chinese_replot_and_aggregate"))
    checks["oldStage11Archived"] = len(archives) == 1 and (archives[0] / "archive_manifest.json").exists()
    aggregate_summary = load(AGGREGATE / "aggregate_plot_audit_summary.json")
    checks["aggregatePass"] = aggregate_summary["gate"] == "PASS_S5_AGGREGATE_PLOT_AUDIT" and aggregate_summary["passedFigures"] == 20
    agg_dirs = sorted(p for p in AGGREGATE.iterdir() if p.is_dir())
    checks["aggregateCountAndSidecars"] = len(agg_dirs) == 20 and all(
        all((p / name).exists() for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_check.md", "sha256.txt", "说明.txt"))
        for p in agg_dirs)
    checks["aggregateFormalOnly"] = all(
        (lambda m: m["sourceFormalCsvSha256"] == EXPECTED and m["interpolation"] == "NONE" and m["smoothing"] == "NONE")(load(p / "plot_manifest.json"))
        for p in agg_dirs) and aggregate_summary["stage12DataMixed"] is False
    with (STAGE11_RESULTS / "s5_scenario_recommendation.csv").open(encoding="utf-8") as stream:
        recommendation = csv.DictReader(stream)
        required = {"primaryCriterion", "fer01Covered", "fer001Covered", "requiredEsN0AtFer01", "requiredEsN0AtFer001",
                    "channelLossAtFer01", "avgDecodeLatencyUs", "p95DecodeLatencyUs", "maxDecodeLatencyUs",
                    "recommendationConfidence", "reason", "limitations"}
        checks["recommendationFieldsUpdated"] = required.issubset(set(recommendation.fieldnames or []))
    checks["noFormalRerunEvidence"] = checks["formalHashUnchanged"]
    gate = "PASS_S5_STAGE11_STAGE12_FINAL_INTEGRATION" if all(checks.values()) else "PARTIAL_PASS_S5_STAGE12_AND_REPLOT"
    final = "PASS_S5_STAGE12_AND_REPLOT_COMPLETE" if gate.startswith("PASS") else "PARTIAL_PASS_S5_STAGE12_AND_REPLOT"
    audit = {"schemaVersion": "s5.stage12_replot.integration.v1", "checks": checks,
             "passed": sum(checks.values()), "total": len(checks), "formalCsvSha256": sha256(FORMAL),
             "stage12Gate": stage12_gate["gate"], "stage11Gate": "PASS_S5_STAGE11_CHINESE_REPLOT" if checks["chineseReplotCount"] else "FAIL",
             "aggregateGate": aggregate_summary["gate"], "integrationGate": gate, "finalGate": final}
    (STAGE11_RESULTS / "chinese_replot_gate.txt").write_text(
        ("PASS_S5_STAGE11_CHINESE_REPLOT" if checks["chineseReplotCount"] else "FAIL_S5_STAGE11_CHINESE_REPLOT") + "\n",
        encoding="utf-8")
    (AGGREGATE / "aggregate_gate.txt").write_text(aggregate_summary["gate"] + "\n", encoding="utf-8")
    (S5 / "S5_STAGE12_AND_REPLOT_FINAL_GATE.txt").write_text(final + "\n", encoding="utf-8")
    (S5 / "S5_STAGE12_AND_REPLOT_AUDIT.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stage_result = S5 / "stages" / "stage11_plot_audit_and_final_integration" / "results"
    stage_result.mkdir(exist_ok=True)
    shutil.copy2(AGGREGATE / "aggregate_plot_audit_summary.json", stage_result / "aggregate_plot_audit_summary.json")
    shutil.copy2(AGGREGATE / "aggregate_manifest.json", stage_result / "aggregate_manifest.json")
    print(final, f"checks={sum(checks.values())}/{len(checks)}")
    return 0 if final.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
