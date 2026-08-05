from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_STAGE_FILES = {"readme.txt", "stage_plan.md", "manifest.json", "validation_report.md", "known_issues.md"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    s7 = Path(__file__).resolve().parents[1]
    repo = s7.parents[2]
    checks: list[str] = []

    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    require(branch == "S7-Comparision", f"wrong branch: {branch}")
    checks.append("PASS_BRANCH")

    require(s7 == repo / "Task" / "Comparison" / "S7", "S7 path is outside frozen scope")
    checks.append("PASS_FROZEN_SCOPE_PATH")

    for number, name in [
        (0, "stage00_repository_audit"), (1, "stage01_scope_and_schema_freeze"),
        (2, "stage02_parameter_freeze"), (3, "stage03_bch_interleavers"),
        (4, "stage04_cc_interleavers"), (5, "stage05_burst_channel"),
        (6, "stage06_bch_chain"), (7, "stage07_cc_chain"),
        (8, "stage08_cpp_matlab_smoke"), (9, "stage09_parameter_prescan")]:
        stage = s7 / name
        require(stage.is_dir(), f"missing {name}")
        missing = REQUIRED_STAGE_FILES - {path.name for path in stage.iterdir() if path.is_file()}
        require(not missing, f"{name} missing {sorted(missing)}")
        manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        require(manifest["stage"] == name and manifest["mergeStatus"] == "NOT_MERGED", f"bad manifest {name}")
        for item in manifest.get("files", []):
            require(item.replace("\\", "/").startswith("Task/Comparison/S7/"), f"manifest path outside S7: {item}")
    checks.append("PASS_STAGE_RECORDS")

    checked_files = []
    for root, directories, files in os.walk(s7):
        directories[:] = [name for name in directories if name not in {"build", "__pycache__"}]
        directory = Path(root)
        relative = directory.relative_to(s7)
        require((directory / "readme.txt").is_file(), f"missing readme: {relative}")
        checked_files.extend(directory / name for name in files)
    checks.append("PASS_README_COVERAGE")

    forbidden = [path for path in checked_files if path.suffix.lower() in {".exe", ".obj", ".pdb"}]
    require(not forbidden, f"generated binary outside build: {forbidden}")
    checks.append("PASS_NO_GENERATED_BINARY")

    smoke = json.loads((s7 / "configs" / "s7_smoke_frozen_config.json").read_text(encoding="utf-8"))
    formal = json.loads((s7 / "configs" / "s7_formal_frozen_config.json").read_text(encoding="utf-8"))
    require(smoke["channel"]["type"] == "AWGN_CONTIGUOUS_BPSK_POLARITY_REVERSAL", "wrong main channel")
    require(smoke["cc"]["permutationUnit"] == "TRELLIS_STEP" and smoke["cc"]["preserveMotherOutputPair"], "bad CC freeze")
    zero = smoke["zeroPolicy"]
    require(zero["rawCsvKeepsZero"] and not zero["plotZeroOnLogAxis"] and not zero["replaceWithPseudoSmallValue"]
            and not zero["extendHorizontalLine"] and not zero["showErrorFloorMarker"]
            and not zero["showZeroErrorUpperBoundMarker"], "bad zero policy")
    require(formal["authorized"] is True and all(value is not None for value in formal["selectedParameters"].values()), "Formal authorization/selection invalid")
    require(formal["formalMatrix"]["totalSchemePoints"] == 4464, "expanded Formal matrix mismatch")
    controlled = formal["ccInterpretationGate"]
    require(controlled["pureMethodDifferenceAllowed"] is False and len(controlled["controlledEqualSpanComparison"]) == 2,
            "CC interpretation Gate missing")
    checks.extend(["PASS_CONFIG", "PASS_ZERO_POLICY", "PASS_FORMAL_AUTHORIZATION_AND_CC_CONTROL"])

    matlab = json.loads((s7 / "stage08_cpp_matlab_smoke" / "results" / "matlab_validation.json").read_text(encoding="utf-8"))
    require(matlab["status"] == "PASS" and matlab["checkCount"] == 72 and matlab["failedCount"] == 0, "MATLAB Gate failed")
    require(Path(matlab["mappingCsvAbsolutePath"]).is_file() and Path(matlab["channelCsvAbsolutePath"]).is_file(), "MATLAB absolute path invalid")
    checks.append("PASS_CPP_MATLAB_72")

    prescan = json.loads((s7 / "stage09_parameter_prescan" / "results" / "prescan_validation.json").read_text(encoding="utf-8"))
    require(prescan["status"] == "PASS" and prescan["rowCount"] == 612 and prescan["candidateCount"] == 17, "prescan Gate failed")
    require(len(prescan["equalSpanMethodComparisonGroups"]) == 4, "equal-span groups missing")
    require(Path(prescan["rawCsvAbsolutePath"]).is_file() and Path(prescan["rankingCsvAbsolutePath"]).is_file(), "prescan absolute path invalid")
    with Path(prescan["rawCsvAbsolutePath"]).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for field in ("BER", "FER", "sigmaSquared", "decodeTimeMeanNs", "deinterleaveTimeMeanNs"):
                require(math.isfinite(float(row[field])), f"NaN/Inf {field}")
    checks.append("PASS_PRESCAN_612")

    archive = s7 / "stage09_parameter_prescan" / "archive"
    versions = sorted(path for path in archive.iterdir() if path.is_dir())
    require(len(versions) == 4, "expected four preserved prescan revisions")
    for version in versions:
        require(re.fullmatch(r"v\d{2}_\d{8}_before_[a-z0-9_]+", version.name) is not None, f"bad archive name {version.name}")
        require((version / "readme.txt").is_file(), f"archive readme missing {version.name}")
    checks.append("PASS_ARCHIVE_INTEGRITY")

    require((s7 / "stage10_bch_formal").is_dir() and (s7 / "current" / "src" / "s7_formal_runner.cpp").is_file(),
            "authorized Stage10 preflight is incomplete")
    checks.append("PASS_READY_TO_START_STAGE10")

    output = {
        "status": "PASS",
        "branch": branch,
        "checkCount": len(checks),
        "checks": checks,
        "stage10Authorized": True,
        "mergeStatus": "NOT_MERGED",
    }
    target = s7 / "stage09_parameter_prescan" / "results" / "stage01_09_gate.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_S7_STAGE01_09_GATE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_S7_STAGE01_09_GATE: {exc}", file=sys.stderr)
        raise
