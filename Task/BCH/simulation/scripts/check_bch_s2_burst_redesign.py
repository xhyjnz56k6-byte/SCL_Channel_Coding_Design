#!/usr/bin/env python3
"""Independent, evidence-producing checker for the S2-07 redesign."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, gate: str) -> None:
    if not value:
        raise RuntimeError(gate)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True
    ).strip()


def run_ctest(repo: Path, audit: Path) -> None:
    build = repo / "Task/BCH/simulation/build/burst_redesign_mingw"
    expected = [
        "bch12_awgn_unit",
        "bch_s2_mmse_unit",
        "bch_s2_impairments_unit",
        "bch_s2_burst_redesign_unit",
    ]
    completed = subprocess.run([
        "ctest", "--test-dir", str(build), "--output-on-failure",
        "-R", "^(" + "|".join(expected) + ")$",
    ], cwd=repo, text=True, stdout=subprocess.PIPE,
       stderr=subprocess.STDOUT)
    log_path = audit / "ctest_log.txt"
    log_path.write_text(completed.stdout, encoding="utf-8")
    require(completed.returncode == 0, "FAIL_BCH_S2_BURST_REDESIGN_CTEST")
    require(all(name in completed.stdout for name in expected),
            "FAIL_BCH_S2_BURST_REDESIGN_CTEST_DISCOVERY")
    require("100% tests passed out of 4" in completed.stdout
            and "***Failed" not in completed.stdout,
            "FAIL_BCH_S2_BURST_REDESIGN_CTEST_COUNT")
    write_rows(audit / "ctest_summary.csv", [{
        "head": git(repo, "rev-parse", "HEAD"),
        "testCount": 4,
        "failedCount": 0,
        "returnCode": completed.returncode,
        "logSha256": sha(log_path),
        "coveredAssertions": (
            "awgn;mmse;impairments;injector;interleaver;"
            "deinterleaver;decoder;unbiased_random_start"
        ),
        "gate": "PASS_BCH_S2_BURST_REDESIGN_CTEST",
    }])


def validate_matlab(repo: Path, audit: Path) -> None:
    execution_path = audit / "matlab_execution.json"
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    require(execution["executed"] is True and execution["skipped"] is False,
            "FAIL_BCH_S2_07_MATLAB_NOT_EXECUTED")
    require(execution["returnCode"] == 0 and execution["gate"] ==
            "PASS_BCH_S2_07_MATLAB_BURST_REFERENCE",
            "FAIL_BCH_S2_07_MATLAB_RETURN_CODE")
    summary_path = repo / execution["outputFile"]
    input_path = repo / execution["inputFile"]
    log_path = repo / execution["logFile"]
    require(sha(input_path) == execution["inputSha256"],
            "FAIL_BCH_S2_07_MATLAB_INPUT_HASH")
    require(sha(summary_path) == execution["outputSha256"],
            "FAIL_BCH_S2_07_MATLAB_OUTPUT_HASH")
    require(sha(log_path) == execution["logSha256"],
            "FAIL_BCH_S2_07_MATLAB_LOG_HASH")
    compared = rows(summary_path)
    mismatch_fields = [
        "encodedMismatch", "burstMismatch", "deinterleaveMismatch",
        "payloadMismatch", "frameMismatch", "statusMismatch",
        "permutationMismatch", "weightMismatch",
    ]
    require(len(compared) == 15, "FAIL_BCH_S2_07_MATLAB_GROUP_COUNT")
    require(sum(int(row["Var3"]) for row in compared) == 9040,
            "FAIL_BCH_S2_07_MATLAB_FRAME_COUNT")
    require(all(row["gate"] == "PASS" for row in compared),
            "FAIL_BCH_S2_07_MATLAB_GATE")
    require(all(int(row[field]) == 0 for row in compared
                for field in mismatch_fields),
            "FAIL_BCH_S2_07_MATLAB_MISMATCH")
    require(subprocess.run([
        "git", "merge-base", "--is-ancestor", execution["head"], "HEAD"
    ], cwd=repo).returncode == 0, "FAIL_BCH_S2_07_MATLAB_HEAD")


def row_is_from_source(
    figure_row: dict[str, str], source_keys: set[tuple[tuple[str, str], ...]]
) -> bool:
    derived = {
        "plotStatus", "guaranteeValue", "overCapabilityFrameFraction",
    }
    key = tuple(sorted(
        (name, value) for name, value in figure_row.items()
        if name not in derived
    ))
    return key in source_keys


def validate_plot_manifest(repo: Path, audit: Path) -> None:
    manifest_path = audit / "plot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["gate"] == "PASS_BCH_S2_07_BURST_PLOT_AUDIT",
            "FAIL_BCH_S2_07_PLOT_MANIFEST_GATE")
    require(manifest["figureCount"] == len(manifest["figures"]) >= 18,
            "FAIL_BCH_S2_07_PLOT_COUNT")
    figure_root = audit / "figures"
    require(not any(path.suffix.lower() in {".jpg", ".jpeg", ".svg", ".pdf"}
                    for path in figure_root.iterdir()),
            "FAIL_BCH_S2_07_NON_PNG_ARTIFACT")
    filenames: set[str] = set()
    for item in manifest["figures"]:
        require(item["filename"] not in filenames,
                "FAIL_BCH_S2_07_DUPLICATE_FIGURE")
        filenames.add(item["filename"])
        image = figure_root / item["filename"]
        figure_data = figure_root / item["figureData"]
        source = Path(item["sourceFile"])
        require(item["format"] == "PNG"
                and image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
                "FAIL_BCH_S2_07_NON_PNG")
        require(sha(image) == item["pngSha256"],
                "FAIL_BCH_S2_07_PNG_HASH")
        require(sha(figure_data) == item["figureDataSha256"],
                "FAIL_BCH_S2_07_FIGURE_DATA_HASH")
        require(source.is_file() and sha(source) == item["sourceSha256"],
                "FAIL_BCH_S2_07_SOURCE_HASH")
        plotted = rows(figure_data)
        source_rows = rows(source)
        require(len(plotted) == int(item["pointCount"]) > 0,
                "FAIL_BCH_S2_07_POINT_COUNT")
        source_keys = {
            tuple(sorted(row.items())) for row in source_rows
        }
        require(all(row_is_from_source(row, source_keys) for row in plotted),
                "FAIL_BCH_S2_07_SOURCE_MAPPING")
        for row in plotted:
            for value in row.values():
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                require(math.isfinite(numeric),
                        "FAIL_BCH_S2_07_NONFINITE_FIGURE_DATA")
            if "guaranteeValue" in row:
                require(int(row["guaranteeValue"]) ==
                        (1 if row["theoreticalGuaranteedRegion"] == "true" else 0),
                        "FAIL_BCH_S2_07_GUARANTEE_DERIVATION")
            if "overCapabilityFrameFraction" in row:
                expected = 1.0 - float(
                    row["fractionAllSubblocksWithinGuaranteedRegion"])
                require(abs(float(row["overCapabilityFrameFraction"]) -
                            expected) <= 1e-15,
                        "FAIL_BCH_S2_07_OVER_CAPABILITY_DERIVATION")
        encodings = item["visualEncoding"]
        style_tuples = [
            (entry["color"], str(entry["linestyle"]), entry["marker"],
             entry.get("markerface", entry["color"]))
            for entry in encodings
            if {"color", "linestyle", "marker"}.issubset(entry)
        ]
        require(len(style_tuples) == len(set(style_tuples)),
                "FAIL_BCH_S2_07_DUPLICATE_VISUAL_ENCODING")
        labels = [
            entry.get("series") or (
                entry.get("caseName", "") + "|" +
                entry.get("channelType", "")
            )
            for entry in encodings if "series" in entry or "caseName" in entry
        ]
        require(len(labels) == len(set(labels)),
                "FAIL_BCH_S2_07_DUPLICATE_LEGEND")
        if "heatmap" in item["filename"] or "local_l1_l5" in item["filename"] \
                or "guarantee_binary" in item["filename"]:
            require(item["interpolation"] == "nearest",
                    "FAIL_BCH_S2_07_HEATMAP_INTERPOLATION")
    required_figures = {
        "bch_s2_07b_s200_local_l1_l5.png",
        "bch_s2_07b_s300_local_l1_l5.png",
        "bch_s2_07b_s200_guarantee_binary.png",
        "bch_s2_07b_s300_guarantee_binary.png",
        "bch_s2_07b_l2_relative_start_fer.png",
        "bch_s2_07d_over_capability_frame_fraction.png",
    }
    require(required_figures.issubset(filenames),
            "FAIL_BCH_S2_07_REQUIRED_FIGURES")
    max_error = next(
        item for item in manifest["figures"]
        if item["filename"] ==
        "bch_s2_07d_segmented_max_subblock_errors.png"
    )
    require(max_error["yLabel"] ==
            "解交织后单个子块最大错误数的帧平均值",
            "FAIL_BCH_S2_07D_MAX_ERROR_LABEL")
    part_a = [
        item for item in manifest["figures"]
        if "_redesigned" in item["filename"]
    ]
    require(len(part_a) == 4 and all(
        item["yScale"] == "log"
        and item["zeroPolicy"] == "OMITTED_ZERO_OBSERVATION"
        for item in part_a
    ), "FAIL_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY")
    for item in part_a:
        for row in rows(figure_root / item["figureData"]):
            expected_snr = float(row["sourcePayloadEbN0Db"]) + \
                10.0 * math.log10(float(row["frameRate"]))
            require(abs(float(row["snrDb"]) - expected_snr) <= 1e-12,
                    "FAIL_BCH_S2_07_SNR_TRANSFORMATION")
            expected_status = (
                "PLOTTED" if float(row["FER"]) > 0
                else "OMITTED_ZERO_OBSERVATION"
            )
            require(row["plotStatus"] == expected_status,
                    "FAIL_BCH_S2_07_ZERO_POLICY")


def run_resume_shard_checker(repo: Path, audit: Path) -> None:
    completed = subprocess.run([
        "python",
        "Task/BCH/simulation/scripts/check_bch_s2_burst_resume_shard.py",
    ], cwd=repo, text=True, stdout=subprocess.PIPE,
       stderr=subprocess.STDOUT)
    log_path = audit / "resume_shard_log.txt"
    log_path.write_text(completed.stdout, encoding="utf-8")
    expected = [
        "PASS_BCH_S2_07_REAL_RESUME",
        "PASS_BCH_S2_07_REAL_THREE_SHARD",
        "PASS_BCH_S2_07_REAL_NEGATIVE_SHARD_REJECTION",
    ]
    require(completed.returncode == 0
            and all(gate in completed.stdout for gate in expected),
            "FAIL_BCH_S2_07_REAL_RESUME_SHARD")


def validate_stage_data(repo: Path, stages: Path) -> dict[str, list[dict[str, str]]]:
    names = {
        "a": "s2_07a_block_burst_correction_boundary",
        "b": "s2_07b_segmented_boundary_heatmap",
        "c": "s2_07c_random_burst_performance",
        "d": "s2_07d_burst_interleaving",
    }
    data = {
        key: rows(stages / name / "formal_summary.csv")
        for key, name in names.items()
    }
    expected_counts = {"a": 45, "b": 900, "c": 185, "d": 370}
    for key, values in data.items():
        require(len(values) == expected_counts[key],
                f"FAIL_BCH_S2_07{key.upper()}_ROW_COUNT")
        require(all(int(row["processedFrames"]) > 0 for row in values),
                f"FAIL_BCH_S2_07{key.upper()}_EMPTY")
        require(all(math.isfinite(float(row["FER"])) for row in values),
                f"FAIL_BCH_S2_07{key.upper()}_NONFINITE")
    guaranteed_a = [
        row for row in data["a"]
        if int(row["burstLength"]) <= int(row["correctionCapabilityT"])
    ]
    require(all(float(row["FER"]) == 0.0 for row in guaranteed_a),
            "FAIL_BCH_S2_07A_GUARANTEED_REGION")
    cross = [
        row for row in data["b"]
        if row["burstLength"] == "2"
        and row["relativeStartInSubblock"] == "14"
    ]
    require(len(cross) == 2 and all(float(row["FER"]) == 0 for row in cross),
            "FAIL_BCH_S2_07B_CROSS_BOUNDARY")
    require(all(row["errorWeightConserved"] == "true" for row in data["d"]),
            "FAIL_BCH_S2_07D_ERROR_WEIGHT_CONSERVATION")
    return data


def validate_git_audit(repo: Path, stages: Path, audit: Path) -> None:
    names = [
        "s2_07a_block_burst_correction_boundary",
        "s2_07b_segmented_boundary_heatmap",
        "s2_07c_random_burst_performance",
        "s2_07d_burst_interleaving",
    ]
    required = {
        "stage_plan.md", "acceptance_matrix.csv", "frozen_config.csv",
        "known_issues.md", "validation_report.md", "test_summary.csv",
        "commands_used.md", "changed_files.md", "manifest.json",
        "changes.patch", "git_commit.txt",
    }
    for name in names:
        root = stages / name
        require(required.issubset({path.name for path in root.iterdir()}),
                "FAIL_BCH_S2_07_AUDIT_FILES")
        stage_manifest = json.loads(
            (root / "manifest.json").read_text(encoding="utf-8"))
        require(stage_manifest["gateStatus"] == "PASS"
                and stage_manifest["mergeStatus"] == "NOT_MERGED",
                "FAIL_BCH_S2_07_MANIFEST_STATE")
        for functional in stage_manifest["functionalRanges"]:
            base, content = functional["baseCommit"], functional["contentCommit"]
            actual = git(repo, "diff", "--name-only", base, content).splitlines()
            require(actual == functional["files"],
                    "FAIL_BCH_S2_07_FUNCTIONAL_RANGE")
            expected_patch = subprocess.check_output(
                ["git", "diff", "--binary", base, content], cwd=repo)
            require((root / "changes.patch").read_bytes() == expected_patch,
                    "FAIL_BCH_S2_07_PATCH_RANGE")
        report = (root / "validation_report.md").read_text(encoding="utf-8")
        require(not any(token in report for token in (
            "Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH")),
            "FAIL_BCH_S2_07_VALIDATION_PLACEHOLDER")
    batch = json.loads((audit / "batch_manifest.json").read_text(
        encoding="utf-8"))
    require(batch["gateStatus"] == "PASS"
            and batch["mergeStatus"] == "NOT_MERGED",
            "FAIL_BCH_S2_07_BATCH_MANIFEST")
    tracked = git(repo, "diff", "--name-only", "origin/main...HEAD").splitlines()
    require(not any(path.startswith(("Task/CC/", "Task/LDPC/"))
                    for path in tracked), "FAIL_BCH_S2_07_SCOPE")
    require(not any(
        "/build/" in path or "/results/" in path
        or path.lower().endswith((".exe", ".obj", ".pdb"))
        for path in tracked), "FAIL_BCH_S2_07_GENERATED_ARTIFACT")


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    audit = stages / "s2_07_burst_redesign_audit"
    validate_stage_data(repo, stages)
    run_ctest(repo, audit)
    validate_matlab(repo, audit)
    run_resume_shard_checker(repo, audit)
    validate_plot_manifest(repo, audit)
    validate_git_audit(repo, stages, audit)
    print("PASS_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY")
    print("PASS_BCH_S2_BURST_REDESIGN_CTEST")
    print("PASS_BCH_S2_07_MATLAB_BURST_REFERENCE")
    print("PASS_BCH_S2_07_REAL_RESUME")
    print("PASS_BCH_S2_07_REAL_THREE_SHARD")
    print("PASS_BCH_S2_07_REAL_NEGATIVE_SHARD_REJECTION")
    print("PASS_BCH_S2_07A_BLOCK_BURST_CORRECTION_BOUNDARY")
    print("PASS_BCH_S2_07B_SEGMENTED_BOUNDARY_HEATMAP")
    print("PASS_BCH_S2_07C_RANDOM_BURST_PERFORMANCE")
    print("PASS_BCH_S2_07D_BURST_INTERLEAVING")
    print("PASS_BCH_S2_07_BURST_PLOT_AUDIT")
    print("PASS_BCH_S2_07_BURST_STRUCTURE_AND_INTERLEAVING")
    print("PASS_BCH_S2_BURST_REDESIGN_AUDIT")
    print("PASS_BCH_S2_BURST_REDESIGN_AND_PLOT_QUALITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
