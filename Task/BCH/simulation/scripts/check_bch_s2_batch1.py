#!/usr/bin/env python3
"""Recompute BCH S2 batch-1 Gates from tracked evidence."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


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
    stage4 = root / "s2_04_fixed_multipath_mmse"
    non_png = [path.name for path in stage4.iterdir()
               if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    if non_png:
        fail("BLOCKED_BCH_S2_04_NON_PNG_ARTIFACT", str(non_png))
    audit = read(stage4 / "figure_data_audit.csv")
    if len(audit) != 24 or any(row["status"] != "PASS" for row in audit):
        fail("BLOCKED_BCH_S2_04_FIGURE_DATA_MISMATCH", "hash audit")
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
    print("PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE")
    print("PASS_BCH_S2_BATCH1_FIXED_MULTIPATH_MMSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
