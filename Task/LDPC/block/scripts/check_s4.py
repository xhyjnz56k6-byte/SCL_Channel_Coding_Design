"""Business and audit checker for the S4-LDPC Stage01-Stage12 batch."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path


STAGES = [
    "stage01_legacy_code_audit",
    "stage02_cc_ldpc_common_contract",
    "stage03_direct_case_selector",
    "stage04_s4_case_freeze",
    "stage05_direct_encoder_matrix",
    "stage06_direct_bp_baseline",
    "stage07_nms_kernel_extraction",
    "stage08_direct_nms_integration",
    "stage09_bp_nms_pairing",
    "stage10_alpha_smoke_scan",
    "stage11_alpha_local_refinement",
    "stage12_direct_bp_nms_smoke",
]
REQUIRED = [
    "readme.txt",
    "stage_plan.md",
    "frozen_config.csv",
    "changed_files.md",
    "validation_report.md",
    "known_issues.md",
    "commands_used.md",
    "manifest.json",
    "changes.patch",
    "git_commit.txt",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, text=True, capture_output=True).stdout.strip()
    require(branch == "stage01-ldpc", f"wrong branch: {branch}")
    status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, text=True, capture_output=True).stdout.splitlines()
    require(all((line[3:] if len(line) > 3 else line).replace("\\", "/").startswith("Task/LDPC/") for line in status), "out-of-scope working-tree change")

    stages_root = root / "Task/LDPC/block/stages"
    for name in STAGES:
        directory = stages_root / name
        require(directory.is_dir(), f"missing stage: {name}")
        for filename in REQUIRED:
            require((directory / filename).is_file(), f"missing {name}/{filename}")
        require((directory / "results").is_dir(), f"missing results: {name}")
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        require(manifest["branch"] == "stage01-ldpc", f"manifest branch: {name}")
        require(manifest["gateStatus"] == "PASS", f"manifest gate: {name}")
        require(manifest["mergeStatus"] == "NOT_MERGED", f"merge status: {name}")
        require(manifest["formalStarted"] is False, f"formal flag: {name}")
        validation = (directory / "validation_report.md").read_text(encoding="utf-8")
        require(not any(token.lower() in validation.lower() for token in ["pending", "to be run", "not_pushed", "to_verify_after_push"]), f"unfinished validation token: {name}")

    cases = read_csv(stages_root / STAGES[3] / "results/frozen_cases.csv")
    require([int(row["actualLength"]) for row in cases] == [480, 560, 640], "frozen lengths")
    for row in cases:
        require(int(row["rankHp"]) == int(row["parityLength"]), f"Hp rank: {row['candidateId']}")
        require(abs(float(row["actualRate"]) - 300.0 / int(row["actualLength"])) < 1e-14, f"actual rate: {row['candidateId']}")

    reference = read_csv(stages_root / STAGES[4] / "results/reference_comparison.csv")
    require(len(reference) == 3 and all(row["status"] == "PASS" for row in reference), "independent reference")
    selfcheck = read_csv(stages_root / STAGES[4] / "results/encoder_selfcheck.csv")
    require(len(selfcheck) == 18 and all(row["status"] == "PASS" for row in selfcheck), "encoder/decoder selfcheck")
    pairing = read_csv(stages_root / STAGES[8] / "results/pairing_hash_check.csv")
    require(len(pairing) == 3 and all(row["status"] == "PASS" for row in pairing), "pairing")

    core = (root / "Task/LDPC/block/current/src/s4_ldpc.cpp").read_text(encoding="utf-8")
    require("rateMatch" not in core and "rateRecover" not in core and "circular buffer" not in core.lower(), "standard-chain dependency in core")

    frozen_alpha = json.loads((stages_root / STAGES[10] / "results/frozen_alpha.json").read_text(encoding="utf-8"))
    require(frozen_alpha["values"] == {"480": 1.0, "560": 1.0, "640": 0.8}, "frozen alpha")
    smoke_dir = stages_root / STAGES[11] / "results"
    smoke = read_csv(smoke_dir / "stage12_smoke_point_results.csv")
    require(len(smoke) == 42, f"smoke row count: {len(smoke)}")
    require(all(row["status"] == "PASS" and int(row["nanInfCount"]) == 0 for row in smoke), "smoke numeric status")
    require(all(0.0 <= float(row["BER"]) <= 1.0 and 0.0 <= float(row["FER"]) <= 1.0 for row in smoke), "BER/FER range")
    require(all(0.0 <= float(row["berCiLow"]) <= float(row["berCiHigh"]) <= 1.0 for row in smoke), "BER CI")
    require(all(0.0 <= float(row["ferCiLow"]) <= float(row["ferCiHigh"]) <= 1.0 for row in smoke), "FER CI")
    require(all(int(row["frameStart"]) >= 10000 for row in smoke), "smoke/calibration separation")
    for path in smoke_dir.glob("*.png"):
        require(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"PNG signature: {path.name}")
        stem = path.with_suffix("")
        require(Path(str(stem) + "_plot_manifest.json").is_file(), f"plot manifest: {path.name}")
        require(Path(str(stem) + "_plot_check.md").is_file(), f"plot check: {path.name}")
    require(len(list(smoke_dir.glob("*.png"))) == 6, "Stage12 plot count")

    forbidden_formal = [path for path in (root / "Task/LDPC").rglob("*") if path.is_dir() and path.name.lower() in {"formal", "formal_coarse", "formal_dense", "waterfall_dense"}]
    require(not forbidden_formal, "formal directory was created")
    print("PASS_STAGE01_TO_STAGE12_S4_LDPC_AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
