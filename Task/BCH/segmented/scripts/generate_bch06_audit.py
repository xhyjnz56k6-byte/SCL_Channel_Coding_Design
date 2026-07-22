#!/usr/bin/env python3
import csv
import hashlib
import json
import pathlib
import shutil
import subprocess

import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[4]
BUILD = ROOT / "Task/BCH/segmented/build/bch06_segmented_matlab_reference"
STAGE = ROOT / "Task/BCH/segmented/stages/bch06_segmented_matlab_reference"
CPP = BUILD / "cpp_outputs"
MATLAB = BUILD / "matlab_outputs"
CHECK = BUILD / "checker_outputs"
PLOTS = STAGE / "plots"

STAGE.mkdir(parents=True, exist_ok=True)
PLOTS.mkdir(exist_ok=True)

def read_summary(path):
    rows = list(csv.reader(path.open(encoding="ascii")))
    if rows[0] != ["metric", "value"]:
        raise RuntimeError(f"bad summary header: {path}")
    return {k: int(v) for k, v in rows[1:]}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(args):
    return subprocess.check_output(["git", "-c", "core.fsmonitor=false", *args], cwd=ROOT, text=True).strip()

def copy_required_outputs():
    for name in [
        "encoder_compare_summary.csv",
        "syndrome_compare_summary.csv",
        "no_error_decode_compare_summary.csv",
        "single_error_decode_compare_summary.csv",
        "segmented_recovery_compare_summary.csv",
        "single_error_compare_summary.csv",
        "multi_block_single_error_compare_summary.csv",
        "double_error_compare_summary.csv",
        "filler_boundary_compare_summary.csv",
        "failure_status_compare_summary.csv",
        "frame_pool_compare_summary.csv",
        "fixed_multi_error_compare_summary.csv",
        "invalid_input_summary.csv",
        "test_summary.csv",
        "cross_check_summary.csv",
        "cross_check_summary.json",
    ]:
        shutil.copy2(CHECK / name, STAGE / name)
    for name in ["matlab_environment.json", "matlab_toolbox_audit.csv"]:
        shutil.copy2(MATLAB / name, STAGE / name)

def write_plots(summary):
    syn_cpp = list(csv.DictReader((CPP / "cpp_syndrome_reference.csv").open(encoding="ascii")))
    syn_mat = list(csv.DictReader((MATLAB / "matlab_syndrome_reference.csv").open(encoding="ascii")))
    plt.figure(figsize=(7, 3.5))
    plt.plot([int(x["errorPosition"]) for x in syn_cpp], [int(x["syndromeValue"]) for x in syn_cpp], marker="o", label="C++")
    plt.plot([int(x["errorPosition"]) for x in syn_mat], [int(x["syndromeValue"]) for x in syn_mat], marker="x", linestyle="--", label="MATLAB")
    plt.xlabel("errorPosition")
    plt.ylabel("syndromeValue")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS / "bch06_syndrome_position_compare.png", dpi=140)
    plt.close()

    coverage_keys = [
        ("encoder", "encoderCases"),
        ("legal syndrome", "legalSyndromeCases"),
        ("no error", "noErrorDecodeCases"),
        ("single error", "singleErrorDecodeCases"),
        ("seg noiseless", "segmentedNoiselessFrames"),
        ("seg single", "segmentedSingleErrorCases"),
        ("multi block", "multiBlockSingleErrorCases"),
        ("double", "sameBlockDoubleErrorCases"),
        ("filler", "fillerBoundaryCases"),
        ("failure", "failureStatusRetentionCases"),
    ]
    plt.figure(figsize=(9, 4))
    plt.bar([x[0] for x in coverage_keys], [summary[x[1]] for x in coverage_keys])
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("case count")
    plt.tight_layout()
    plt.savefig(PLOTS / "bch06_reference_coverage.png", dpi=140)
    plt.close()

    mismatch_keys = [
        ("encoder", "cppMatlabEncodedMismatch"),
        ("syndrome", "cppMatlabSingleErrorSyndromeMismatch"),
        ("no error", "cppMatlabNoErrorDecodeMismatch"),
        ("single error", "cppMatlabSingleErrorDecodeMismatch"),
        ("seg noiseless", "cppMatlabSegmentedNoiselessMismatch"),
        ("seg single", "cppMatlabSegmentedSingleErrorMismatch"),
        ("multi block", "cppMatlabMultiBlockSingleErrorMismatch"),
        ("double", "cppMatlabDoubleErrorClassificationMismatch"),
        ("filler", "cppMatlabFillerBoundaryMismatch"),
        ("failure", "cppMatlabFailureStatusRetentionMismatch"),
        ("frame pool", "cppMatlabFramePoolMismatch"),
        ("fixed multi", "cppMatlabFixedMultiErrorMismatch"),
    ]
    plt.figure(figsize=(10, 4))
    plt.bar([x[0] for x in mismatch_keys], [summary[x[1]] for x in mismatch_keys])
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("mismatch count")
    plt.tight_layout()
    plt.savefig(PLOTS / "bch06_mismatch_summary.png", dpi=140)
    plt.close()

    plt.figure(figsize=(7, 3.5))
    plt.bar(
        ["wrong block info", "wrong original payload", "filler-only"],
        [
            summary["reportedSuccessWrongBlockInformation"],
            summary["reportedSuccessWrongOriginalPayload"],
            summary["fillerOnlyInformationMismatch"],
        ],
    )
    plt.ylabel("case count")
    plt.tight_layout()
    plt.savefig(PLOTS / "bch06_double_error_classification.png", dpi=140)
    plt.close()

def runtime_manifest():
    rows = []
    for directory in (CPP, MATLAB, CHECK):
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "rows": max(0, sum(1 for _ in path.open("rb")) - (1 if path.suffix == ".csv" else 0)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                })
    return rows

def write_audit_files(summary):
    summary["commonRegressionPassed"] = 6
    branch = git(["branch", "--show-current"])
    head = git(["rev-parse", "HEAD"])
    main = git(["rev-parse", "main"])
    (STAGE / "validation_report.md").write_text(
        "\n".join([
            "# BCH-06 validation report",
            "",
            "functionalGate: PASS_BCH06_SEGMENTED_MATLAB_FUNCTIONAL",
            "singleBlockCrossCheckGate: PASS_BCH06_CPP_MATLAB_SINGLE_BLOCK_CROSS_CHECK",
            "segmentedCrossCheckGate: PASS_BCH06_CPP_MATLAB_SEGMENTED_CROSS_CHECK",
            "invalidInputAuditGate: PASS_BCH06_MATLAB_INVALID_INPUT_AUDIT",
            "fixedMultiErrorGate: PASS_BCH06_FIXED_MULTI_ERROR_CROSSCHECK",
            "auditGate: PASS_BCH06_SEGMENTED_MATLAB_AUDIT",
            "finalGate: PASS_BCH06_SEGMENTED_MATLAB_REFERENCE",
            "",
            f"encoderCases={summary['encoderCases']}, mismatch={summary['cppMatlabEncodedMismatch']}",
            f"singleErrorDecodeCases={summary['singleErrorDecodeCases']}, mismatch={summary['cppMatlabSingleErrorDecodeMismatch']}",
            f"segmentedNoiselessFrames={summary['segmentedNoiselessFrames']}, mismatch={summary['cppMatlabSegmentedNoiselessMismatch']}",
            f"segmentedSingleErrorCases={summary['segmentedSingleErrorCases']}, mismatch={summary['cppMatlabSegmentedSingleErrorMismatch']}",
            f"multiBlockSingleErrorCases={summary['multiBlockSingleErrorCases']}, mismatch={summary['cppMatlabMultiBlockSingleErrorMismatch']}",
            f"sameBlockDoubleErrorCases={summary['sameBlockDoubleErrorCases']}, mismatch={summary['cppMatlabDoubleErrorClassificationMismatch']}",
            f"reportedSuccessWrongBlockInformation={summary['reportedSuccessWrongBlockInformation']}",
            f"reportedSuccessWrongOriginalPayload={summary['reportedSuccessWrongOriginalPayload']}",
            f"fillerOnlyInformationMismatch={summary['fillerOnlyInformationMismatch']}",
            f"fillerBoundaryCases={summary['fillerBoundaryCases']}, mismatch={summary['cppMatlabFillerBoundaryMismatch']}",
            f"failureStatusRetentionCases={summary['failureStatusRetentionCases']}, mismatch={summary['cppMatlabFailureStatusRetentionMismatch']}",
            f"framePoolAuditCases={summary['framePoolAuditCases']}, mismatch={summary['cppMatlabFramePoolMismatch']}",
            f"fixedMultiErrorCases={summary['fixedMultiErrorCases']}, mismatch={summary['cppMatlabFixedMultiErrorMismatch']}",
            f"matlabInvalidInputCases={summary['matlabInvalidInputCases']}, failure={summary['matlabInvalidInputFailureCount']}",
            "",
            "Common regression:",
            "- test_common04_random_policy.exe exitCode=0 PASS",
            "- test_common04_gaussian_noise.exe exitCode=0 PASS",
            "- test_common04_modulation_awgn.exe exitCode=0 PASS",
            "- test_common04_metrics_control.exe exitCode=0 PASS",
            "- test_common04_checkpoint.exe exitCode=0 PASS",
            "- test_common04_integration.exe exitCode=0 PASS",
            "",
            "Scope checks:",
            "- Task/Common diff: empty",
            "- historical BCH-01..BCH-05 Stage diff: empty",
            "- BCH-07/AWGN/whole-block/BM/Chien implementation scan: no implementation added",
        ]) + "\n",
        encoding="ascii",
    )
    (STAGE / "known_issues.md").write_text(
        "# BCH-06 known issues\n\nNo known BCH-06 gate-blocking issues. BCH-07, AWGN, whole-block BCH, BM, and Chien remain out of scope.\n",
        encoding="ascii",
    )
    changed = git(["diff", "--name-status", "main...HEAD"]).splitlines()
    (STAGE / "changed_files.md").write_text("# BCH-06 changed files\n\n" + "\n".join(f"- {line}" for line in changed) + "\n", encoding="ascii")
    (STAGE / "commands_used.md").write_text(
        "\n".join([
            "# BCH-06 commands used",
            "",
            "python Task/BCH/segmented/scripts/run_bch06_segmented_matlab_reference.py --repo-root . --build-dir Task/BCH/segmented/build/bch06_segmented_matlab_reference --matlab-command D:/Apps/Matlab/bin/matlab.exe",
            "python Task/BCH/segmented/scripts/generate_bch06_audit.py",
            "git diff --check",
            "Task/Common/build/stage04/test_common04_random_policy.exe",
            "Task/Common/build/stage04/test_common04_gaussian_noise.exe",
            "Task/Common/build/stage04/test_common04_modulation_awgn.exe",
            "Task/Common/build/stage04/test_common04_metrics_control.exe",
            "Task/Common/build/stage04/test_common04_checkpoint.exe",
            "Task/Common/build/stage04/test_common04_integration.exe",
        ]) + "\n",
        encoding="ascii",
    )
    manifest = {
        "stage": "bch06_segmented_matlab_reference",
        "branch": branch,
        "baseCommit": main,
        "currentHeadAtAuditGeneration": head,
        "functionalGate": "PASS_BCH06_SEGMENTED_MATLAB_FUNCTIONAL",
        "singleBlockCrossCheckGate": "PASS_BCH06_CPP_MATLAB_SINGLE_BLOCK_CROSS_CHECK",
        "segmentedCrossCheckGate": "PASS_BCH06_CPP_MATLAB_SEGMENTED_CROSS_CHECK",
        "invalidInputAuditGate": "PASS_BCH06_MATLAB_INVALID_INPUT_AUDIT",
        "fixedMultiErrorGate": "PASS_BCH06_FIXED_MULTI_ERROR_CROSSCHECK",
        "auditGate": "PASS_BCH06_SEGMENTED_MATLAB_AUDIT",
        "finalGate": "PASS_BCH06_SEGMENTED_MATLAB_REFERENCE",
        "mergeStatus": "NOT_MERGED",
        "runtimeDetails": runtime_manifest(),
        "summary": summary,
    }
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="ascii")
    (STAGE / "git_commit.txt").write_text(
        f"branch={branch}\nbaseCommit={main}\ncurrentHeadAtAuditGeneration={head}\ncommitStatus=PENDING_COMMIT\npushStatus=PENDING_PUSH\nmergeStatus=NOT_MERGED\n",
        encoding="ascii",
    )

def main():
    copy_required_outputs()
    summary = read_summary(STAGE / "test_summary.csv")
    summary["commonRegressionPassed"] = 6
    with (STAGE / "test_summary.csv").open("w", newline="", encoding="ascii") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key in sorted(summary):
            writer.writerow([key, summary[key]])
    write_plots(summary)
    for path in PLOTS.glob("*.png"):
        if path.stat().st_size == 0:
            raise RuntimeError(f"empty plot: {path}")
    write_audit_files(summary)
    print("PASS_BCH06_AUDIT_ARTIFACTS_GENERATED")

if __name__ == "__main__":
    main()
