#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


STAGE_DIR = Path("Task/Common/stages/stage04_common_simulation_foundation")
TESTS = [
    ("G1", "PASS_COMMON_RANDOM_POLICY", "test_common04_random_policy.exe"),
    ("G2", "PASS_COMMON_GAUSSIAN_NOISE", "test_common04_gaussian_noise.exe"),
    ("G3", "PASS_COMMON_BPSK_AWGN_LLR", "test_common04_modulation_awgn.exe"),
    ("G4", "PASS_COMMON_METRICS_CONTROL", "test_common04_metrics_control.exe"),
    ("G5", "PASS_COMMON_CHECKPOINT_RESULTS", "test_common04_checkpoint.exe"),
    ("G6", "PASS_COMMON_INTEGRATION", "test_common04_integration.exe"),
]
FORBIDDEN_DIFF_PREFIXES = ("Task/BCH/", "Task/CC/", "Task/LDPC/", "Task/Common/Plan/", "初始规划/")
FORBIDDEN_ARTIFACT_SUFFIXES = (".exe", ".obj", ".pdb", ".pyc")


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, text=True, capture_output=True)


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def require_file(path: Path, failures: list[str]) -> None:
    if not path.exists() or path.stat().st_size == 0:
        add_failure(failures, f"missing or empty file: {path}")


def check_acceptance(root: Path, failures: list[str]) -> None:
    matrix = root / STAGE_DIR / "acceptance_matrix.csv"
    frozen = root / STAGE_DIR / "frozen_config.csv"
    plan = root / STAGE_DIR / "stage_plan.md"
    for path in [matrix, frozen, plan]:
        require_file(path, failures)
    rows = list(csv.DictReader(matrix.open(encoding="utf-8")))
    if len(rows) < 46:
        add_failure(failures, "acceptance matrix must contain at least 46 rows")
    required_ids = {"G1-002", "G2-004", "G2-005", "G2-006", "G2-009", "G3-002", "G3-003", "G5-001", "G6-006", "AUD-004", "AUD-005"}
    ids = {row["requirementId"] for row in rows}
    missing = sorted(required_ids - ids)
    if missing:
        add_failure(failures, f"acceptance matrix missing ids: {missing}")
    config = {row["key"]: row["value"] for row in csv.DictReader(frozen.open(encoding="utf-8"))}
    for key in ["defaultNoiseGroupId", "noisePoolSchemaVersion", "noiseShardMagic", "noiseShardHeaderVersion",
                "gaussianSanitySampleCount", "formalMinFrames", "formalMaxFrames", "formalTargetFrameErrors",
                "checkpointSchemaVersion", "resultSchemaVersion", "metadataSchemaVersion", "configHashAlgorithm",
                "identityCodeType", "hardDecisionAtZero", "llrSignConvention"]:
        if key not in config:
            add_failure(failures, f"frozen_config missing {key}")


def check_source_scope(root: Path, failures: list[str]) -> None:
    scan_paths = [
        root / "Task/Common/include/common",
        root / "Task/Common/src",
        root / "Task/Common/tests/stage04",
    ]
    common04_scripts = [
        root / "Task/Common/scripts/build_common04.py",
        root / "Task/Common/scripts/generate_common04_noise_pool.py",
        root / "Task/Common/scripts/validate_common04_noise_pool.py",
        root / "Task/Common/scripts/inspect_common04_noise_pool.py",
        root / "Task/Common/scripts/compare_common04_cpp_python.py",
        root / "Task/Common/scripts/merge_common04_shards.py",
        root / "Task/Common/scripts/plot_common_results.py",
    ]
    joined = ""
    for folder in scan_paths:
        if folder.exists():
            for path in folder.rglob("*"):
                if path.name == "check_common04.py":
                    continue
                if path.is_file() and path.suffix in {".hpp", ".cpp", ".py"}:
                    joined += path.read_text(encoding="utf-8", errors="ignore") + "\n"
    for path in common04_scripts:
        if path.is_file():
            joined += path.read_text(encoding="utf-8", errors="ignore") + "\n"
    forbidden = [
        "std::normal_" + "distribution",
        "random_" + "device",
        "Vit" + "erbi",
        "Layered " + "BP",
        "N" + "MS",
        "O" + "MS",
        "inter" + "leave(",
        "deinter" + "leave(",
    ]
    for marker in forbidden:
        if marker in joined:
            add_failure(failures, f"forbidden implementation marker found: {marker}")


def check_git_scope(root: Path, failures: list[str]) -> None:
    diff = run(["git", "diff", "--name-status", "main...HEAD"], root)
    if diff.returncode != 0:
        add_failure(failures, diff.stderr.strip())
        return
    for line in diff.stdout.splitlines():
        parts = line.split("\t", 1)
        path = parts[-1].replace("\\", "/") if parts else ""
        if path.startswith(FORBIDDEN_DIFF_PREFIXES):
            add_failure(failures, f"forbidden path in Stage04 diff: {path}")
        if path.startswith("Task/Common/build/") or path.startswith("Task/Common/results/"):
            add_failure(failures, f"generated path in Stage04 diff: {path}")
        if path.endswith(FORBIDDEN_ARTIFACT_SUFFIXES) or "__pycache__/" in path:
            add_failure(failures, f"artifact path in Stage04 diff: {path}")


def check_audit_manifest(root: Path, failures: list[str]) -> None:
    manifest_path = root / STAGE_DIR / "manifest.json"
    if not manifest_path.exists():
        add_failure(failures, "missing Stage04 manifest.json")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest.get("baseCommit", "")
    functional = manifest.get("functionalCommit", "")
    if not base or not functional:
        add_failure(failures, "manifest must record baseCommit and functionalCommit")
        return
    diff = run(["git", "diff", "--name-status", f"{base}...{functional}"], root)
    if diff.returncode != 0:
        add_failure(failures, diff.stderr.strip())
        return
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for line in diff.stdout.splitlines():
        status, path = line.split("\t", 1)
        path = path.replace("\\", "/")
        if status == "A":
            added.append(path)
        elif status == "M":
            modified.append(path)
        elif status == "D":
            deleted.append(path)
    if sorted(manifest.get("added", [])) != sorted(added):
        add_failure(failures, "manifest added list mismatch")
    if sorted(manifest.get("modified", [])) != sorted(modified):
        add_failure(failures, "manifest modified list mismatch")
    if sorted(manifest.get("deleted", [])) != sorted(deleted):
        add_failure(failures, "manifest deleted list mismatch")
    if manifest.get("remoteVerificationStatus") != "VERIFIED":
        add_failure(failures, "manifest remoteVerificationStatus must be VERIFIED")
    if manifest.get("mergeStatus") != "NOT_MERGED":
        add_failure(failures, "manifest mergeStatus must be NOT_MERGED")
    remote_branch = manifest.get("remoteBranch", "")
    remote_ref = run(["git", "rev-parse", "--verify", remote_branch], root)
    if remote_ref.returncode != 0:
        add_failure(failures, "manifest remoteBranch is not available")
    else:
        ancestor = run(["git", "merge-base", "--is-ancestor", functional, remote_ref.stdout.strip()], root)
        if ancestor.returncode != 0:
            add_failure(failures, "functional commit is not contained in remote branch")
    validation = (root / STAGE_DIR / "validation_report.md").read_text(encoding="utf-8", errors="ignore")
    for token in ["Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"]:
        if token in validation:
            add_failure(failures, f"validation_report contains stale token: {token}")


def check_noise_pool_scripts(root: Path, failures: list[str]) -> None:
    out = root / "Task/Common/build/stage04/python_noise_pool"
    if out.exists():
        shutil.rmtree(out)
    generated = run([sys.executable, "Task/Common/scripts/generate_common04_noise_pool.py",
                     "--output-dir", str(out), "--frame-count", "60", "--symbols-per-frame", "20",
                     "--frames-per-shard", "25", "--overwrite"], root)
    if generated.returncode != 0:
        add_failure(failures, generated.stderr + generated.stdout)
        return
    manifest = out / "manifest.json"
    validated = run([sys.executable, "Task/Common/scripts/validate_common04_noise_pool.py", str(manifest)], root)
    if validated.returncode != 0:
        add_failure(failures, validated.stderr + validated.stdout)
    repeated = run([sys.executable, "Task/Common/scripts/generate_common04_noise_pool.py",
                    "--output-dir", str(out), "--frame-count", "60"], root)
    if repeated.returncode == 0 or "overwrite" not in (repeated.stderr + repeated.stdout):
        add_failure(failures, "noise generator overwrite negative test failed")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data["totalFrames"] != 60 or len(data["shards"]) != 3:
        add_failure(failures, "noise pool shard count mismatch")
    inspected = run([sys.executable, "Task/Common/scripts/inspect_common04_noise_pool.py", str(manifest)], root)
    if inspected.returncode != 0:
        add_failure(failures, inspected.stderr + inspected.stdout)


def check_results_and_plots(root: Path, failures: list[str]) -> None:
    out = root / "Task/Common/build/stage04/results"
    out.mkdir(parents=True, exist_ok=True)
    summary = out / "summary.csv"
    header = "schemaVersion,experimentId,stage,codeType,caseName,payloadLength,encodedLength,codeRate,ebN0_dB,snrIndex,processedFrames,totalPayloadBits,bitErrors,frameErrors,successfulFrames,ber,fer,successRate,avgEncodeTimeUs,avgChannelTimeUs,avgDecodeTimeUs,maxDecodeTimeUs,avgRecoveryTimeUs,avgTotalTimeUs,maxTotalTimeUs,stopReason,framePoolId,noisePoolId,configHash\n"
    rows = [
        "common04.result_summary.v1,exp,stage04_common_simulation_foundation,IDENTITY,k200,200,248,0.8064516,0,0,100,20000,2000,80,20,0.1,0.8,0.2,0,0,0,0,0,0,0,MAX_FRAMES,frame,noise,hash\n",
        "common04.result_summary.v1,exp,stage04_common_simulation_foundation,IDENTITY,k200,200,248,0.8064516,4,1,100,20000,200,20,80,0.01,0.2,0.8,0,0,0,0,0,0,0,MAX_FRAMES,frame,noise,hash\n",
    ]
    summary.write_text(header + "".join(rows), encoding="utf-8")
    plotted = run([sys.executable, "Task/Common/scripts/plot_common_results.py", "--input", str(summary), "--output-dir", str(out / "plots")], root)
    if plotted.returncode != 0:
        add_failure(failures, plotted.stderr + plotted.stdout)
    for png in ["ber_vs_ebn0.png", "fer_vs_ebn0.png", "success_rate_vs_ebn0.png", "avg_decode_time_vs_ebn0.png", "max_decode_time_vs_ebn0.png", "avg_total_time_vs_ebn0.png"]:
        require_file(out / "plots" / png, failures)
    empty = out / "empty.csv"
    empty.write_text(header, encoding="utf-8")
    empty_plot = run([sys.executable, "Task/Common/scripts/plot_common_results.py", "--input", str(empty), "--output-dir", str(out / "bad")], root)
    if empty_plot.returncode == 0:
        add_failure(failures, "empty CSV plot negative test failed")


def main() -> int:
    root = Path(__file__).resolve().parents[2].parents[0]
    # __file__ = repo/Task/Common/scripts/check_common04.py, so root above is repo/Task.
    root = Path(__file__).resolve().parents[3]
    failures: list[str] = []
    check_acceptance(root, failures)
    build = run([sys.executable, "Task/Common/scripts/build_common04.py"], root)
    if build.returncode != 0:
        add_failure(failures, build.stdout + build.stderr)
    else:
        build_dir = root / "Task/Common/build/stage04"
        for gate_name, gate, exe in TESTS:
            completed = run([str(build_dir / exe)], root)
            if completed.returncode != 0:
                add_failure(failures, f"{gate_name} failed: {completed.stdout}{completed.stderr}")
                break
            print(f"COMMON-04 {gate_name} CHECK: PASS")
            print(f"Gate: {gate}")
    check_noise_pool_scripts(root, failures)
    compare = run([sys.executable, "Task/Common/scripts/compare_common04_cpp_python.py"], root)
    if compare.returncode != 0:
        add_failure(failures, compare.stdout + compare.stderr)
    check_results_and_plots(root, failures)
    check_source_scope(root, failures)
    check_git_scope(root, failures)
    check_audit_manifest(root, failures)
    for script, expected in [
        ("Task/Common/scripts/check_common02.py", "COMMON-02 CHECK: PASS"),
        ("Task/Common/scripts/check_common03.py", "COMMON-03 CHECK: PASS"),
    ]:
        completed = run([sys.executable, script], root)
        if completed.returncode != 0 or expected not in completed.stdout:
            add_failure(failures, f"regression failed: {script}\n{completed.stdout}{completed.stderr}")
    if failures:
        print("COMMON-04 CHECK: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("COMMON-04 CHECK: PASS")
    print("Gate: PASS_COMMON_SIMULATION_FOUNDATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
