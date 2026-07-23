#!/usr/bin/env python3
"""One-command BCH-16V official MATLAB AWGN validation driver."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_FROM_SCRIPT = Path(__file__).resolve().parents[5]
VALIDATION_RELATIVE = Path("Task/BCH/simulation/matlab_official_validation")


def run(command: list[str], cwd: Path) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def hash_config(config: dict[str, object]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def formal_plan(path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["caseName"] in {"BCH-S200", "BCH-B200"}]
    expected = {
        "BCH-S200": [round(4.5 + 0.2 * index, 1) for index in range(21)],
        "BCH-B200": [round(3.5 + 0.2 * index, 1) for index in range(13)] + [6.0],
    }
    for case, grid in expected.items():
        selected = [row for row in rows if row["caseName"] == case]
        actual = [round(float(row["ebn0Db"]), 1) for row in selected]
        if actual != grid:
            raise SystemExit("BLOCKED_BCH16V_FORMAL_CONFIG_MISMATCH")
        if len({int(row["snrIndex"]) for row in selected}) != len(selected):
            raise SystemExit("BLOCKED_BCH16V_FORMAL_CONFIG_MISMATCH")
    totals = {case: sum(int(row["processedFrames"]) for row in rows if row["caseName"] == case)
              for case in expected}
    return rows, totals


def locate_matlab(requested: str | None) -> str:
    if requested:
        return requested
    found = shutil.which("matlab")
    if found:
        return found
    fallback = Path(r"D:\Apps\Matlab\bin\matlab.exe")
    if fallback.is_file():
        return str(fallback)
    raise SystemExit("BLOCKED_BCH16V_COMMUNICATIONS_TOOLBOX_UNAVAILABLE")


def matlab_quote(path: Path | str) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def write_input_manifest_copy(runtime_manifest: Path, stage_dir: Path, repo: Path) -> None:
    data = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    data["payloadManifest"] = str(Path(data["payloadManifest"]).resolve().relative_to(repo)).replace("\\", "/")
    data["formalSummary"] = str(Path(data["formalSummary"]).resolve().relative_to(repo)).replace("\\", "/")
    for point in data["points"]:
        point["noiseFile"] = f"<generated-input>/{point['noiseFile']}"
        point["cppReferenceFile"] = f"<generated-input>/{point['cppReferenceFile']}"
    (stage_dir / "shared_input_manifest.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_results(results: Path, stage: Path) -> None:
    mappings = {
        results / "matlab_official" / "matlab_environment.json": "matlab_environment.json",
        results / "matlab_official" / "official_parameter_audit.csv": "official_parameter_audit.csv",
        results / "matlab_official" / "official_encoding_compare_summary.csv": "official_encoding_compare_summary.csv",
        results / "matlab_official" / "official_representative_decode_summary.csv": "official_representative_decode_summary.csv",
        results / "matlab_official" / "matlab_official_formal_summary.csv": "matlab_official_formal_summary.csv",
        results / "matlab_official" / "paired_frame_error_contingency.csv": "paired_frame_error_contingency.csv",
        results / "comparison" / "cpp_matlab_official_summary_compare.csv": "cpp_matlab_official_summary_compare.csv",
        results / "comparison" / "target_fer_interpolation_compare.csv": "target_fer_interpolation_compare.csv",
        results / "figures" / "plot_manifest.json": "plot_manifest.json",
    }
    for source, name in mappings.items():
        if source.is_file():
            shutil.copy2(source, stage / name)
    for pattern in ("*.png", "figure_data_*.csv"):
        for source in (results / "figures").glob(pattern):
            shutil.copy2(source, stage / source.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT_FROM_SCRIPT)
    parser.add_argument("--cpp-formal-summary", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--matlab-command")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--progress-refresh-seconds", type=float)
    parser.add_argument("--checkpoint-interval", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--generate-input-only", action="store_true")
    parser.add_argument("--matlab-only", action="store_true")
    parser.add_argument("--compare-only", action="store_true")
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    validation = repo / VALIDATION_RELATIVE
    config_path = (args.config or validation / "configs/bch16v_official_awgn_config.json").resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if args.batch_size:
        config["batchSize"] = args.batch_size
    if args.progress:
        config["progressEnabled"] = True
    if args.no_progress:
        config["progressEnabled"] = False
    if args.progress_refresh_seconds:
        config["progressRefreshSeconds"] = args.progress_refresh_seconds
    if args.checkpoint_interval:
        config["checkpointIntervalFrames"] = args.checkpoint_interval
    config["resume"] = args.resume
    config["configHash"] = hash_config(config)
    formal = (args.cpp_formal_summary or repo / str(config["formalSummary"])).resolve()
    frame_pool = (repo / str(config["framePoolManifest"])).resolve()
    input_dir = (args.input_dir or validation / "input/shared_payload_noise").resolve()
    results = (args.results_dir or validation / "results").resolve()
    stage = validation / "stages/bch16v_matlab_official_awgn_curve_reference"
    runtime_config = results / "runtime_config.json"
    rows, totals = formal_plan(formal)
    matlab = locate_matlab(args.matlab_command)

    print("BCH-16V execution plan")
    print("Cases: BCH-S200, BCH-B200")
    print("SNR points:", len(rows))
    for case in ("BCH-S200", "BCH-B200"):
        print(case, [(float(row["ebn0Db"]), int(row["processedFrames"])) for row in rows if row["caseName"] == case])
    print("Total frames:", totals, "overall", sum(totals.values()))
    print("Shared input: payload + standard Gaussian z")
    print("MATLAB command:", matlab)
    print("Output:", results)
    print("Progress:", config["progressEnabled"], "refresh", config["progressRefreshSeconds"],
          "checkpoint", config["checkpointIntervalFrames"])
    if args.dry_run:
        return 0

    results.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    stage.mkdir(parents=True, exist_ok=True)
    runtime_config.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    selected = any((args.generate_input_only, args.matlab_only, args.compare_only, args.plot_only, args.audit_only))
    do_input = args.all or args.generate_input_only or not selected
    do_matlab = args.all or args.matlab_only or not selected
    do_compare = args.all or args.compare_only or not selected
    do_plot = args.all or args.plot_only or not selected
    do_audit = args.all or args.audit_only or not selected

    build = validation / "build_mingw"
    exporter = build / "bch16v_export_shared_input.exe"
    if do_input:
        print("[1/9] Read formal configuration")
        run(["cmake", "-G", "MinGW Makefiles", "-S", str(validation), "-B", str(build)], repo)
        run(["cmake", "--build", str(build), "--target", "bch16v_export_shared_input", "-j", "4"], repo)
        print("[2/9] Generate shared inputs")
        command = [str(exporter), "--formal-summary", str(formal), "--frame-pool-manifest", str(frame_pool),
                   "--output-dir", str(input_dir), "--progress" if config["progressEnabled"] else "--no-progress"]
        run(command, repo)
        write_input_manifest_copy(input_dir / "shared_input_manifest.json", stage, repo)
        (stage / "cpp_formal_source_manifest.json").write_text(json.dumps({
            "path": str(formal.relative_to(repo)).replace("\\", "/"),
            "sha256": sha256(formal),
            "sourceCommit": subprocess.check_output(["git", "rev-parse", "main"], cwd=repo, text=True).strip(),
            "casePointCount": len(rows),
            "processedFrames": totals,
        }, indent=2) + "\n", encoding="utf-8")
        if args.generate_input_only:
            return 0
    manifest = input_dir / "shared_input_manifest.json"
    if not manifest.is_file():
        raise SystemExit("BLOCKED_BCH16V_SHARED_INPUT_HASH_MISMATCH")

    if do_matlab:
        print("[3/9] Validate official encoding")
        print("[4/9] Validate representative hard decisions")
        print("[5/9] Run MATLAB S200")
        print("[6/9] Run MATLAB B200")
        matlab_results = results / "matlab_official"
        matlab_results.mkdir(parents=True, exist_ok=True)
        matlab_dir = validation / "matlab"
        expression = (
            f"addpath('{matlab_quote(matlab_dir)}');"
            f"run_bch16v_official_awgn('{matlab_quote(runtime_config)}','{matlab_quote(manifest)}',"
            f"'{matlab_quote(matlab_results)}',{str(args.resume).lower()})"
        )
        run([matlab, "-batch", expression], repo)
        if args.matlab_only:
            return 0
    if do_compare:
        print("[7/9] Compare results")
        comparison = results / "comparison"
        run([sys.executable, str(validation / "scripts/compare_cpp_matlab_official.py"),
             "--cpp-formal-summary", str(formal),
             "--matlab-summary", str(results / "matlab_official/matlab_official_formal_summary.csv"),
             "--paired", str(results / "matlab_official/paired_frame_error_contingency.csv"),
             "--output-dir", str(comparison)], repo)
        if args.compare_only:
            return 0
    if do_plot:
        print("[8/9] Plot four PNG figures")
        run([sys.executable, str(validation / "scripts/plot_bch16v_cpp_vs_matlab.py"),
             "--compare", str((results / "comparison/cpp_matlab_official_summary_compare.csv").relative_to(repo)),
             "--cpp-source", str(formal.relative_to(repo)),
             "--matlab-source", str((stage / "matlab_official_formal_summary.csv").relative_to(repo)),
             "--output-dir", str(results / "figures")], repo)
        if args.plot_only:
            return 0
    if do_audit:
        print("[9/9] Final audit")
        copy_results(results, stage)
        run([sys.executable, str(validation / "scripts/audit_bch16v.py"),
             "--results-dir", str(results), "--stage-dir", str(stage)], repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
