#!/usr/bin/env python3
"""Recompute BCH S2 batch-1 Gates from tracked evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def finite_float(value: object, code: str, detail: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        fail(code, detail)
    if not math.isfinite(number):
        fail(code, detail)
    return number


def check_figure_data(stage: Path, item: dict[str, object]) -> None:
    rows = read(stage / str(item["figureDataCsv"]))
    if not rows:
        fail("BLOCKED_BCH_S2_04_EMPTY_FIGURE_DATA", str(item["filename"]))
    plotted_count = 0
    omitted_count = 0
    y_column = str(item["yColumn"])
    for index, row in enumerate(rows, start=1):
        plotted = row.get("plotted", "true").lower() != "false"
        if plotted:
            plotted_count += 1
        else:
            omitted_count += 1
        if item["xColumn"] == "snrDb":
            snr = finite_float(row.get("snrDb", ""),
                               "BLOCKED_BCH_S2_04_NONFINITE_VALUE",
                               f"{item['filename']}:{index}:snrDb")
            if row.get("sourcePayloadEbN0Db", "") and row.get("frameRate", ""):
                source_ebn0 = finite_float(row["sourcePayloadEbN0Db"],
                                           "BLOCKED_BCH_S2_04_NONFINITE_VALUE",
                                           f"{item['filename']}:{index}:sourcePayloadEbN0Db")
                frame_rate = finite_float(row["frameRate"],
                                          "BLOCKED_BCH_S2_04_NONFINITE_VALUE",
                                          f"{item['filename']}:{index}:frameRate")
                if frame_rate <= 0.0:
                    fail("BLOCKED_BCH_S2_04_X_FORMULA_INVALID_RATE", f"{item['filename']}:{index}")
                expected = source_ebn0 + 10.0 * math.log10(frame_rate)
                if abs(snr - expected) > 5e-10:
                    fail("BLOCKED_BCH_S2_04_X_FORMULA_MISMATCH", f"{item['filename']}:{index}")
        if not plotted and (row.get(y_column, "") == "" or row.get("valid", "").lower() == "false"):
            continue
        if row.get(y_column, "") == "":
            fail("BLOCKED_BCH_S2_04_Y_VALUE_MISSING", f"{item['filename']}:{index}:{y_column}")
        y_value = finite_float(row[y_column], "BLOCKED_BCH_S2_04_NONFINITE_VALUE",
                               f"{item['filename']}:{index}:{y_column}")
        if item["yScale"] == "log" and y_value <= 0.0:
            fail("BLOCKED_BCH_S2_04_LOG_Y_NONPOSITIVE", f"{item['filename']}:{index}:{y_column}")
    if plotted_count != int(item.get("validatedDataPointCount", -1)):
        fail("BLOCKED_BCH_S2_04_POINT_COUNT_MISMATCH", str(item["filename"]))
    if omitted_count != int(item.get("omittedRowCount", -1)):
        fail("BLOCKED_BCH_S2_04_OMITTED_COUNT_MISMATCH", str(item["filename"]))


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    root = repo / "Task/BCH/simulation/stages"
    if subprocess.run(["git", "branch", "--show-current"], cwd=repo, check=True,
                      text=True, stdout=subprocess.PIPE).stdout.strip() == "main":
        fail("BLOCKED_BCH_S2_AUDIT_ON_MAIN", "current branch is main")
    required = [
        "s2_01_channel_contract", "s2_02_multi_channel_foundation",
        "s2_03_awgn_baseline_reuse", "s2_04_fixed_multipath_mmse",
    ]
    for name in required:
        stage = root / name
        for filename in [
            "stage_plan.md", "acceptance_matrix.csv", "frozen_config.csv",
            "validation_report.md", "test_summary.csv", "changed_files.md",
            "commands_used.md", "known_issues.md", "manifest.json",
            "changes.patch", "git_commit.txt",
        ]:
            if not (stage / filename).is_file():
                fail("BLOCKED_BCH_S2_AUDIT_FILE_MISSING", f"{name}/{filename}")
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        if manifest["mergeStatus"] != "NOT_MERGED":
            fail("BLOCKED_BCH_S2_MERGE_STATUS", name)
        for item in manifest["functionalRanges"]:
            actual = subprocess.run(
                ["git", "diff", "--name-only",
                 f"{item['baseCommit']}...{item['contentCommit']}"],
                cwd=repo, check=True, text=True, stdout=subprocess.PIPE,
            ).stdout.splitlines()
            if actual != item["files"]:
                fail("BLOCKED_BCH_S2_MANIFEST_DIFF_MISMATCH", name)
        validation = (stage / "validation_report.md").read_text(encoding="utf-8")
        for forbidden in ["Pending", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"]:
            if forbidden in validation:
                fail("BLOCKED_BCH_S2_AUDIT_STATE_CONFLICT", f"{name}:{forbidden}")

    formal = read(root / "s2_04_fixed_multipath_mmse/formal_summary.csv")
    formal_sha = hashlib.sha256(
        (root / "s2_04_fixed_multipath_mmse/formal_summary.csv").read_bytes()
    ).hexdigest().upper()
    if formal_sha != "ECDAB168917C606B9ED06805463E1DECE7F0F3C5E129B3800B5EA71845C5B649":
        fail("BLOCKED_BCH_S2_04_FORMAL_SUMMARY_CHANGED", formal_sha)
    if len(formal) != 145:
        fail("BLOCKED_BCH_S2_04_FORMAL_POINT_INCOMPLETE", str(len(formal)))
    cases = {row["caseName"] for row in formal}
    if len(cases) != 5:
        fail("BLOCKED_BCH_S2_01_CASE_CONFIG_MISMATCH", str(cases))
    for row in formal:
        frames = int(row["processedFrames"])
        if int(row["trueSuccessFrames"]) + int(row["decodedFrameErrors"]) != frames:
            fail("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY", row["caseName"])
        if int(row["reportedSuccessFrames"]) + int(row["decoderFailureFrames"]) != frames:
            fail("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY", row["caseName"])
        expected_snr = float(row["sourcePayloadEbN0Db"]) + 10 * math.log10(float(row["frameRate"]))
        if abs(float(row["snrDb"]) - expected_snr) >= 1e-12:
            fail("BLOCKED_BCH_S2_03_SNR_CONVERSION_MISMATCH", row["caseName"])
        if any(not math.isfinite(float(row[field])) for field in
               ["BER", "FER", "avgEqualizationTimeUs", "avgDecodeTimeUs"]):
            fail("BLOCKED_BCH_S2_04_METRIC_INCONSISTENCY", "non-finite")
    loss = read(root / "s2_04_fixed_multipath_mmse/multipath_loss_summary.csv")
    if len(loss) != 15:
        fail("BLOCKED_BCH_S2_04_INVALID_INTERPOLATION", "target row count")
    invalid = [row for row in loss if row["valid"] != "true"]
    if any(row["multipathLowerBracket"] == "" or row["multipathUpperBracket"] == ""
           for row in loss):
        fail("BLOCKED_BCH_S2_04_FORMAL_GRID_INVALID", "multipath target not bracketed")
    expected_invalid = {("BCH-S200", "0.001"), ("BCH-B300", "0.001")}
    actual_invalid = {(row["caseName"], f"{float(row['targetFer']):.3g}") for row in invalid}
    if actual_invalid != expected_invalid or any(
       "AWGN:TARGET_NOT_BRACKETED_NO_EXTRAPOLATION" not in row["reason"]
       for row in invalid):
        fail("BLOCKED_BCH_S2_04_INVALID_INTERPOLATION", str(actual_invalid))
    overlap = read(root / "s2_04_fixed_multipath_mmse/fer_amplification_overlap_audit.csv")
    if len(overlap) != 5:
        fail("BLOCKED_BCH_S2_04_FER_AMPLIFICATION_OVERLAP_AUDIT", "row count")
    if any(row["publicationStatus"] == "CURVE_ALLOWED" and
           int(row["validOverlapPointCount"]) < 2 for row in overlap):
        fail("BLOCKED_BCH_S2_04_FER_AMPLIFICATION_OVERLAP_AUDIT", "curve with fewer than two points")
    if any(row["publicationStatus"] == "SINGLE_POINT_ONLY" and
           int(row["validOverlapPointCount"]) != 1 for row in overlap):
        fail("BLOCKED_BCH_S2_04_FER_AMPLIFICATION_OVERLAP_AUDIT", "single point count mismatch")
    resume = read(root / "s2_04_fixed_multipath_mmse/resume_shard_audit.csv")
    if len(resume) != 2 or any(row["status"] != "PASS" for row in resume):
        fail("BLOCKED_BCH_S2_04_CHECKPOINT_RESUME_MISMATCH", "equivalence")
    matlab = read(root / "s2_04_fixed_multipath_mmse/matlab_reference_summary.csv")
    if len(matlab) != 15 or any(row["gate"] != "PASS" or
       int(float(row["hardBitMismatches"])) != 0 or
       int(float(row["decodedPayloadBitMismatches"])) != 0 or
       int(float(row["decodedFrameErrorMismatches"])) != 0 for row in matlab):
        fail("BLOCKED_BCH_S2_04_MATLAB_HARD_DECISION_MISMATCH", "MATLAB summary")
    plot = json.loads((root / "s2_04_fixed_multipath_mmse/plot_manifest.json").read_text(encoding="utf-8"))
    if len(plot["figures"]) != 24:
        fail("BLOCKED_BCH_S2_04_FIGURE_DATA_MISMATCH", "PNG count")
    for item in plot["figures"]:
        if item["legendLabelCount"] != item["uniqueLegendLabelCount"]:
            fail("BLOCKED_BCH_S2_04_LEGEND_LABEL_DUPLICATE", item["filename"])
        if item["xColumn"] == "snrDb" and item["xLabel"] != "SNR (dB)":
            fail("BLOCKED_BCH_S2_04_AXIS_LABEL_MISMATCH", item["filename"])
        if item["xColumn"] == "snrDb" and str(item.get("xTransformFormula", "")) != (
                "snrDb=sourcePayloadEbN0Db+10*log10(frameRate); normalized waveform SNR uses Bn=Rs"):
            fail("BLOCKED_BCH_S2_04_X_FORMULA_MISSING", item["filename"])
        check_figure_data(root / "s2_04_fixed_multipath_mmse", item)
        if item["filename"] == "bch_s2_receiver_time_comparison.png" and item[
                "totalReceiverTimingScope"] != "EQUALIZATION_HARD_DECISION_ERROR_ACCOUNTING_DECODE_AND_AUDIT":
            fail("BLOCKED_BCH_S2_04_TOTAL_RECEIVER_SCOPE_MISSING", item["filename"])
    stage4 = root / "s2_04_fixed_multipath_mmse"
    non_png = [path.name for path in stage4.iterdir()
               if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if non_png:
        fail("BLOCKED_BCH_S2_04_NON_PNG_ARTIFACT", str(non_png))
    audit = read(stage4 / "figure_data_audit.csv")
    if len(audit) != 24 or any(row["status"] != "PASS" for row in audit):
        fail("BLOCKED_BCH_S2_04_FIGURE_DATA_MISMATCH", "hash audit")
    if any(row["legendLabelCount"] != row["uniqueLegendLabelCount"] for row in audit):
        fail("BLOCKED_BCH_S2_04_LEGEND_LABEL_DUPLICATE", "figure_data_audit.csv")
    changed = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"], cwd=repo, check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    forbidden = [path for path in changed if path.startswith(("Task/CC/", "Task/LDPC/", "Task/Common/Plan/"))
                 or "/build/" in path or "/results/" in path
                 or path.lower().endswith((".exe", ".obj", ".pdb"))]
    if forbidden:
        fail("BLOCKED_BCH_S2_SCOPE_VIOLATION", str(forbidden))
    print("PASS_BCH_S2_01_CHANNEL_CONTRACT")
    print("PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION")
    print("SKIPPED_BCH_S2_03_AWGN_RERUN")
    print("REUSED_S1_FORMAL_AWGN_BASELINE")
    print("PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE_FUNCTIONAL")
    print("PASS_BCH_S2_BATCH1_STRICT_AUDIT_CLEANUP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
