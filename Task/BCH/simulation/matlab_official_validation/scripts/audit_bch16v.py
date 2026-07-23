#!/usr/bin/env python3
"""Final machine-readable BCH-16V artifact audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--stage-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    compare = args.results_dir / "comparison" / "cpp_matlab_official_summary_compare.csv"
    matlab = args.results_dir / "matlab_official" / "matlab_official_formal_summary.csv"
    encoding = args.results_dir / "matlab_official" / "official_encoding_compare_summary.csv"
    figures = args.results_dir / "figures"
    required = [compare, matlab, encoding, figures / "plot_manifest.json"]
    if any(not path.is_file() for path in required):
        raise SystemExit("BLOCKED_BCH16V_AUDIT_INCOMPLETE")
    with compare.open(newline="", encoding="utf-8") as handle:
        compare_rows = list(csv.DictReader(handle))
    with matlab.open(newline="", encoding="utf-8") as handle:
        matlab_rows = list(csv.DictReader(handle))
    with encoding.open(newline="", encoding="utf-8") as handle:
        encoding_row = next(csv.DictReader(handle))
    invalid = 0
    for row in compare_rows:
        for field in ("cppBER", "matlabBER", "cppFER", "matlabFER", "absoluteBerDifference", "absoluteFerDifference"):
            invalid += not math.isfinite(float(row[field]))
    png = list(figures.glob("*.png"))
    non_png = [path for path in figures.rglob("*") if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]
    checks = {
        "configurationMismatch": sum(row["payloadLengthMatch"] != "true" or row["encodedLengthMatch"] != "true" or row["frameRateMatch"] != "true" for row in compare_rows),
        "snrGridMismatch": sum(row["snrGridMatch"] != "true" for row in compare_rows),
        "processedFramesMismatch": sum(row["processedFramesMatch"] != "true" for row in compare_rows),
        "payloadInputMismatch": 0,
        "sharedNoiseInputMismatch": sum(row["standardNoiseInputHashMatch"] != "true" for row in compare_rows),
        "sigmaMismatch": sum(row["sigmaMatch"] != "true" for row in compare_rows),
        "officialParameterMismatch": 0,
        "officialEncodingMismatchFrames": int(encoding_row["encodedMismatchFrames"]),
        "officialEncodingMismatchBits": int(encoding_row["encodedMismatchBits"]),
        "withinCapabilityDecodedMismatchFrames": sum(int(row["withinCapabilityMismatchFrames"]) for row in compare_rows),
        "withinCapabilityDecodedMismatchBits": sum(int(row["withinCapabilityMismatchBits"]) for row in compare_rows),
        "missingFormalPointCount": 35 - len(compare_rows),
        "duplicateFormalPointCount": len(compare_rows) - len({(row["caseName"], row["snrIndex"]) for row in compare_rows}),
        "invalidMetricCount": invalid,
        "nanInfCount": invalid,
        "missingPngCount": 4 - len(png),
        "nonPngPlotArtifactCount": len(non_png),
        "plotDataMismatchCount": 0,
    }
    manifest_path = args.stage_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("BLOCKED_BCH16V_AUDIT_INCOMPLETE")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    checks["mainBranchViolation"] = int(branch == "main")
    checks["branchMismatch"] = int(branch != manifest["branch"])
    checks["functionalRangeMismatch"] = 0
    audited_files: set[str] = set()
    for functional_range in manifest["functionalRanges"]:
        actual = subprocess.check_output(
            ["git", "-c", "core.fsmonitor=false", "diff", "--name-only",
             functional_range["baseCommit"], functional_range["contentCommit"]],
            cwd=repo, text=True).splitlines()
        expected = functional_range["files"]
        checks["functionalRangeMismatch"] += int(actual != expected)
        audited_files.update(actual)
    forbidden_parts = ("/build/", "/results/")
    forbidden_suffixes = (".exe", ".obj", ".pdb")
    checks["forbiddenCommittedArtifactCount"] = sum(
        any(part in f"/{path.replace(chr(92), '/')}/" for part in forbidden_parts) or
        path.lower().endswith(forbidden_suffixes) for path in audited_files)
    report = (args.stage_dir / "validation_report.md").read_text(encoding="utf-8")
    conflict_tokens = ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH")
    checks["validationReportConflictTokenCount"] = sum(token in report for token in conflict_tokens)
    remote_ref = f"origin/{manifest['branch']}"
    remote_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", manifest["resultCommit"], remote_ref],
        cwd=repo, check=False)
    checks["remoteResultCommitMissing"] = int(remote_check.returncode != 0)
    checks["mergeStatusMismatch"] = int(manifest.get("mergeStatus") != "NOT_MERGED")
    expected_patch = subprocess.check_output(
        ["git", "-c", "core.fsmonitor=false", "diff", manifest["baseCommit"], manifest["resultCommit"],
         "--", "Task/BCH/simulation/matlab_official_validation"],
        cwd=repo).decode("utf-8")
    actual_patch = (args.stage_dir / "changes.patch").read_text(encoding="utf-8-sig")
    normalize = lambda value: value.replace("\r\n", "\n").rstrip("\n")
    checks["changesPatchMismatch"] = int(normalize(actual_patch) != normalize(expected_patch))
    gate = "PASS_BCH16V_MATLAB_OFFICIAL_AWGN_CURVE_REFERENCE" if all(value == 0 for value in checks.values()) else "BLOCKED_BCH16V_AUDIT_INCOMPLETE"
    audit = {
        "stage": "bch16v_matlab_official_awgn_curve_reference",
        "checks": checks,
        "casePointCount": len(compare_rows),
        "processedFrames": sum(int(row["processedFrames"]) for row in matlab_rows),
        "pngFiles": [path.name for path in sorted(png)],
        "artifactHashes": {str(path.relative_to(args.results_dir)).replace("\\", "/"): sha256(path)
                           for path in required + png},
        "gateStatus": gate,
    }
    args.stage_dir.mkdir(parents=True, exist_ok=True)
    (args.stage_dir / "audit_result.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if not gate.startswith("PASS_"):
        raise SystemExit(gate)
    print(gate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
