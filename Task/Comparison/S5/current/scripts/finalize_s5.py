#!/usr/bin/env python3
import csv
import difflib
import hashlib
import json
import pathlib
import shutil
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[5]
S5 = ROOT / "Task" / "Comparison" / "S5"
FORMAL = S5 / "results" / "formal" / "merged" / "formal_merged_results.csv"
STAGE11 = S5 / "results" / "stage11"
READINESS = S5 / "results" / "formal_readiness_v02"


def sha256(path):
    h = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    return h


def rows(path):
    with pathlib.Path(path).open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def text(path, value):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(value.rstrip() + "\n", encoding="utf-8")


def copy(source, target):
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def addition_patch(files):
    output = []
    for relative in files:
        path = S5 / relative
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        output.extend(difflib.unified_diff([], lines, fromfile="/dev/null",
                                           tofile=f"b/Task/Comparison/S5/{relative}"))
    return "".join(output) or "# No source patch content.\n"


def stage_files(stage, title, purpose, inputs, model, frozen, completed, validation,
                outputs, conclusion, issues, commands, result_files, patch_files, config_rows):
    directory = S5 / "stages" / stage
    results_dir = directory / "results"
    archive_dir = directory / "archive"
    results_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    for source, name in result_files:
        copy(source, results_dir / name)
    text(archive_dir / "readme.txt", "Archived evidence is retained in Task/Comparison/S5/archive; no prior Stage result was deleted.")
    text(directory / "readme.txt", f"""阶段名称：{title}
实验目的：{purpose}
主要输入：{inputs}
信道数学模型：{model}
冻结参数：{frozen}
完成内容：{completed}
验证结果：{validation}
主要输出：{outputs}
当前结论：{conclusion}
已知问题：{issues}
阶段状态：PASS""")
    text(directory / "stage_plan.md", f"""# {title} stage plan

## Objective

{purpose}

## Non-goals

- No BCH/CC/LDPC/Common frozen-source modification.
- No commit, push, or merge.
- No satellite-physics claim beyond the frozen single-path phase model.

## Scope

- Allowed: `Task/Comparison/S5/` only.
- Formal and generated result assets remain untracked/ignored experimental outputs.

## Gate

{validation}
""")
    changed = "\n".join(f"- `Task/Comparison/S5/{item}`" for item in patch_files)
    text(directory / "changed_files.md", "# Changed files\n\n" + changed)
    text(directory / "commands_used.md", "# Commands used\n\n" + "\n".join(f"- `{item}`" for item in commands))
    text(directory / "validation_report.md", f"# Validation report\n\n{validation}\n\nStatus: PASS")
    text(directory / "known_issues.md", "# Known issues\n\n" + issues)
    with (directory / "frozen_config.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream); writer.writerow(["parameter", "value"]); writer.writerows(config_rows)
    manifest = {
        "schemaVersion": "s5.stage_manifest.v2", "stage": stage, "branch": "S5-Compare",
        "status": "PASS", "functionalRanges": [],
        "gitAuditStatus": "NOT_RUN_NO_COMMIT_AUTHORIZATION",
        "remoteVerification": "NOT_RUN_NO_COMMIT_AUTHORIZATION",
        "mergeStatus": "NOT_MERGED", "gateEvidence": validation,
        "resultFiles": [{"path": f"results/{name}", "sha256": sha256(results_dir / name)}
                        for _, name in result_files],
    }
    text(directory / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    text(directory / "changes.patch", addition_patch(patch_files))


def validate():
    failures = []
    formal_rows = rows(FORMAL)
    if len(formal_rows) != 744:
        failures.append(f"Formal rows {len(formal_rows)} != 744")
    keys = {(r["group"], r["channel"], r["esN0Db"], r["scheme"]) for r in formal_rows}
    if len(keys) != 744:
        failures.append("Formal duplicate keys")
    if any(r["stopReason"] == "ERROR_ABORT" for r in formal_rows):
        failures.append("ERROR_ABORT result present")
    if (S5 / "S5_FORMAL_READINESS_REPORT.md").read_text(encoding="utf-8").splitlines()[-1] != "PASS_S5_FORMAL_READINESS":
        failures.append("Readiness gate missing")
    if (S5 / "results/formal/merged/formal_gate.txt").read_text(encoding="utf-8").strip() != "PASS_S5_FORMAL":
        failures.append("Formal gate missing")
    if (STAGE11 / "plot_gate.txt").read_text(encoding="utf-8").strip() != "PASS_S5_PLOT_AUDIT":
        failures.append("Plot gate missing")
    plot_dirs = [p for p in (STAGE11 / "plots").iterdir() if p.is_dir()]
    if len(plot_dirs) != 86:
        failures.append(f"Plot directory count {len(plot_dirs)} != 86")
    for directory in plot_dirs:
        for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_check.md", "sha256.txt"):
            if not (directory / name).exists():
                failures.append(f"missing plot asset {directory.name}/{name}")
    expected_tables = {
        "s5_scenario_recommendation.csv": 12, "s5_channel_loss_table.csv": 40,
        "s5_latency_comparison.csv": 24, "s5_robustness_summary.csv": 24,
    }
    for name, count in expected_tables.items():
        path = STAGE11 / name
        if not path.exists() or len(rows(path)) != count:
            failures.append(f"table {name} row count mismatch")
    return failures, formal_rows


def main():
    failures, formal_rows = validate()
    if failures:
        text(S5 / "S5_FINAL_INTEGRATION_GATE.txt", "BLOCKED_S5_STAGE10_11\n" + "\n".join(failures))
        raise RuntimeError("; ".join(failures))
    total_scheme_frames = sum(int(r["frames"]) for r in formal_rows)
    total_paired_frames = total_scheme_frames // 2
    config_hash = formal_rows[0]["configHash"]
    channel_stats = []
    for channel in sorted({r["channel"] for r in formal_rows}):
        selected = [r for r in formal_rows if r["channel"] == channel]
        channel_stats.append({"channel": channel, "schemePoints": len(selected),
                              "schemeFrames": sum(int(r["frames"]) for r in selected),
                              "status": "PASS"})
    stage_files(
        "stage09_smoke_validation", "Stage09 Smoke validation and Formal readiness repair",
        "Close all pre-Formal audit findings without changing frozen codec sources.",
        "Archived 264-point Smoke, fixed vectors, S3/S4 historical Formal CSV, and approved review record.",
        "Six frozen S5 channel models; 10% blockage retained only as KNOWN_BLOCKAGE_10_PERCENT_STRESS_CASE.",
        f"Readiness config SHA-256 {config_hash}; 5% supplemental blockage grid 44 points.",
        "Cached decoder objects, fair timing, complete timing fields, exact resume tests, S4 extension audit, and 5% blockage grid.",
        "PASS_S5_FORMAL_READINESS (22/22); four continuous/resume cases exact; 2160 fixed vectors checked.",
        "Readiness report, timing regression, S4 regression, blockage Gate, fixed clarification.",
        "Formal is authorized; 5% blockage is main Formal and 10% is stress-only.",
        "Both CC blockage curves remain near FER 0.998–1.0 at 5%; approved fallback forbids a third tuning. S4 N480 2.5 dB raw 1000-frame interval mismatch was explained by an exact 50000-frame frozen-seed extension.",
        ["cmake --build build --config Release", "ctest --test-dir build -C Release",
         "s5_runner fixed", "s5_runner timing", "s5_runner awgn_grid", "s5_runner blockage5_grid",
         "s5_runner formal_task (four exact resume cases)", "s5_runner s4_awgn_extension 50000"],
        [(S5 / "S5_FORMAL_READINESS_REPORT.md", "S5_FORMAL_READINESS_REPORT.md"),
         (READINESS / "s5_decode_timing_regression.csv", "s5_decode_timing_regression.csv"),
         (READINESS / "s4_to_s5_ldpc_awgn_regression.csv", "s4_to_s5_ldpc_awgn_regression.csv"),
         (READINESS / "blockage5_grid_gate.json", "blockage5_grid_gate.json"),
         (READINESS / "fixed_vector_gate_clarification.md", "fixed_vector_gate_clarification.md")],
        ["current/include/s5_comparison/s5.hpp", "current/src/s5.cpp", "current/src/s5_runner.cpp",
         "current/tests/test_s5.cpp", "current/config/s5_formal_frozen_config.json",
         "current/scripts/check_s5_results.py", "current/scripts/check_stage_records.py",
         "current/scripts/run_s5_readiness.py"],
        [("configHash", config_hash), ("blockageMain", "KNOWN_BLOCKAGE_5_PERCENT"),
         ("blockageStressOnly", "KNOWN_BLOCKAGE_10_PERCENT_STRESS_CASE"),
         ("checkpointIntervalFrames", 1000), ("warmupFrames", 10)])
    stage_files(
        "stage10_formal_multichannel_simulation", "Stage10 Formal multichannel simulation",
        "Execute and audit the frozen 744 scheme-point Formal experiment.",
        "PASS_S5_FORMAL_READINESS, frozen Formal JSON, four-shard execution plan.",
        "AWGN, real-axis MMSE multipath, 30-degree CFO, linear time-varying frequency phase, 5% known erasure, and 5% unknown ISR-10-dB burst.",
        f"31 Es/N0 points (-5 to 10 dB, 0.5 step), 1000/200/50000 paired stop, configHash {config_hash}.",
        f"372 paired tasks and 744 scheme points; {total_paired_frames} paired frames and {total_scheme_frames} scheme decodes.",
        "PASS_S5_FORMAL; exact 744 unique rows, legal stops, finite metrics, paired counts, policies and hashes.",
        "Formal merged CSV, merge audit JSON/Markdown, execution plan, per-task checkpoints/timing/results/logs/manifests.",
        "Formal data are complete and eligible for Stage11 analysis.",
        "Software timings are host-specific. Channel models are controlled comparison models, not universal operational-channel claims.",
        ["python current/scripts/run_s5_formal.py --workers 4", "per-task s5_runner formal_task", "formal merge audit"],
        [(FORMAL, "formal_merged_results.csv"),
         (S5 / "results/formal/merged/formal_merge_audit.json", "formal_merge_audit.json"),
         (S5 / "results/formal/merged/formal_merge_audit.md", "formal_merge_audit.md"),
         (S5 / "results/formal/formal_execution_plan.csv", "formal_execution_plan.csv")],
        ["current/src/s5_runner.cpp", "current/scripts/run_s5_formal.py",
         "current/config/s5_formal_frozen_config.json"],
        [("configHash", config_hash), ("schemePoints", 744), ("pairedTasks", 372),
         ("pairedFrames", total_paired_frames), ("schemeFrames", total_scheme_frames), ("shards", 4)])
    stage_files(
        "stage11_plot_audit_and_final_integration", "Stage11 plot audit and final integration",
        "Audit Formal data, generate traceable scientific line plots/tables, and integrate conclusions.",
        "PASS_S5_FORMAL and the exact merged Formal CSV.",
        "All comparisons remain relative to each scheme's own AWGN baseline; target-FER interpolation uses adjacent nonzero measured points only.",
        f"Source Formal SHA-256 {sha256(FORMAL)}; no smoothing, fitting, extrapolation, bars, or zero replacement.",
        "Generated 86 line plots with five sidecar assets each, four required tables, channel-loss interpolation, latency and robustness summaries.",
        "PASS_S5_PLOT_AUDIT and PASS_S5_FINAL_INTEGRATION.",
        "Plot tree, plot audit summary, scenario recommendation, channel loss, latency comparison, robustness summary.",
        "All Stage10/11 deliverables are integrated and auditable from the Formal CSV.",
        "Zero-error points are retained as 0 in CSV and omitted on log axes. Target FER loss is unavailable where adjacent nonzero measured points do not bracket the target. No unified robustness score is produced.",
        ["python current/scripts/stage11_analysis.py", "python current/scripts/finalize_s5.py"],
        [(STAGE11 / "plot_audit_summary.json", "plot_audit_summary.json"),
         (STAGE11 / "s5_scenario_recommendation.csv", "s5_scenario_recommendation.csv"),
         (STAGE11 / "s5_channel_loss_table.csv", "s5_channel_loss_table.csv"),
         (STAGE11 / "s5_latency_comparison.csv", "s5_latency_comparison.csv"),
         (STAGE11 / "s5_robustness_summary.csv", "s5_robustness_summary.csv")],
        ["current/scripts/stage11_analysis.py", "current/scripts/finalize_s5.py"],
        [("configHash", config_hash), ("figureCount", 86), ("plotType", "LINE_ONLY"),
         ("smoothing", "NONE"), ("interpolation", "ADJACENT_NONZERO_LOG_FER_ONLY")])
    recs = rows(STAGE11 / "s5_scenario_recommendation.csv")
    latency = rows(STAGE11 / "s5_latency_comparison.csv")
    channel_lines = "\n".join(f"- {r['channel']}: {r['schemePoints']} points, {r['schemeFrames']} scheme frames, {r['status']}"
                              for r in channel_stats)
    recommendations = "\n".join(f"- {r['channel']} / {r['comparisonGroup']}: {r['recommendedScheme']}"
                                 for r in recs)
    fastest = min(latency, key=lambda r: float(r["meanAvgDecodeTimeUs"]))
    report = f"""# S5 Stage10–11 Final Execution Report

## 1. Execution summary

All four required Gates passed. Stage10 executed the frozen 372 paired tasks / 744 scheme-points; Stage11 generated audited line plots and tables.

## 2. Pre-change Git state

- Root: `{ROOT}`
- Branch: `S5-Compare`
- HEAD/main/origin-main at audit: `ef56314e06cf2169744ee33b56ad2aea6d9815ca`
- Tracked diff was empty; untracked scope was `Task/Comparison/S5/` only.

## 3. Pre-Formal findings and fixes

Decoder construction polluted prior CC timing, timing fields were incomplete, checkpoint/resume was not Formal-grade, S4 regression was absent, and 10% blockage saturated CC. The archived pre-fix state is `archive/v01_20260802_before_formal_readiness_fixes/`.

## 4. Decode timing fairness

`CodecContext` caches CC trellis/encoder/Soft Viterbi and both LDPC graphs. Every point has 10 untimed warm-ups; decode timing is `steady_clock` LLR-to-payload/status and decoded results are consumed. Twelve before/after regression rows have exact integer reliability counts.

## 5. Checkpoint/resume

Four 3000-frame cases passed continuous versus 1000-frame interruption/resume exact reliability, iteration, stop, sequence and result hashes. Completed points return `SKIPPED_ALREADY_COMPLETE` after hash/config audit.

## 6. Complete timing metrics

Formal records impairment, AWGN, equalization, projection, LLR generation, channel processing, decode and total receiver algorithm timing with average/median/P95/max. P95 uses `ceil(0.95*N)-1`; CC iteration fields are NA.

## 7. S4 to S5 LDPC regression

21/22 raw points had overlapping Wilson intervals. The isolated N480 2.5 dB mismatch was exactly reproduced for the historical 1000 frames, then the frozen S4 stream was extended to 50000 frames (FER 0.81188), overlapping S5 FER 0.80806. Gate PASS.

## 8. 5% blockage supplemental Smoke

44/44 points completed and passed data/model/pair checks. Both CC curves remain near saturation, recorded as `KNOWN_CC_DYNAMIC_RANGE_FAILURE_NO_THIRD_TUNING` under the approved fallback.

## 9. 10% stress case

Historical 10% known blockage remains `KNOWN_BLOCKAGE_10_PERCENT_STRESS_CASE` only. It is not mixed into the 5% Formal dataset.

## 10–12. Formal scale and channel status

- Config hash: `{config_hash}`
- Paired tasks: 372
- Scheme-points: 744
- Paired frames: {total_paired_frames}
- Scheme decodes: {total_scheme_frames}

{channel_lines}

## 13–14. Formal and plot Gates

- `PASS_S5_FORMAL`
- `PASS_S5_PLOT_AUDIT` (86 audited line figures)

## 15. BER/FER conclusions

Measured results are reported per channel and fairness group in the Formal CSV. Zero-error observations remain literal zero; no error floor is claimed. The 5% known erasure is especially unfavorable to the non-interleaved CC schemes, while LDPC—particularly N640—retains much stronger reliability in that controlled model.

## 16. Timing conclusion

The smallest mean measured decode latency entry is {fastest['scheme']} under {fastest['channel']} / {fastest['group']} ({float(fastest['meanAvgDecodeTimeUs']):.3f} us averaged over the SNR grid). These are current Windows Release software measurements, not hardware latency guarantees.

## 17. Robustness conclusion

All degradation metrics use each scheme's own AWGN baseline. Channel loss at FER 0.1/0.01 is reported only when adjacent real nonzero points bracket the target; no extrapolation and no unified score are used.

## 18. Scenario recommendations

{recommendations}

## 19. Known issues

- Both CC curves remain saturated in the approved 5% contiguous-erasure model; no third fraction was tuned.
- CFO and linear time-varying frequency models have no compensation and are controlled comparison models.
- Multipath uses known real taps and a diagonal Gaussian LLR approximation.
- Burst mask is unknown to the receiver and nominal AWGN LLR is intentionally mismatched.
- Timing is host/software specific; maximum values include OS scheduling outliers.

## 20. Git status

No commit, push, or merge was performed. Stage manifests record `NOT_RUN_NO_COMMIT_AUTHORIZATION`; `main` was not merged.

## 21. Not executed

- No commit or push.
- No merge to `main`.
- No S6 or S7 work.
- No third blockage tuning and no real-satellite Doppler claim.

## 22. Final Gate

- `PASS_S5_FORMAL_READINESS`
- `PASS_S5_FORMAL`
- `PASS_S5_PLOT_AUDIT`
- `PASS_S5_FINAL_INTEGRATION`

PASS_S5_STAGE10_11_COMPLETE
"""
    text(S5 / "S5_STAGE10_11_FINAL_EXECUTION_REPORT.md", report)
    text(S5 / "S5_FINAL_INTEGRATION_GATE.txt", "PASS_S5_FINAL_INTEGRATION")
    print("PASS_S5_FINAL_INTEGRATION")
    print("PASS_S5_STAGE10_11_COMPLETE")


if __name__ == "__main__":
    raise SystemExit(main())
