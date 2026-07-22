#!/usr/bin/env python3
"""Publish curated BCH Group 4 evidence and perform artifact-level checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


FORBIDDEN_PLOT_SUFFIXES = {".pdf", ".svg", ".eps", ".ps"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_bch12(results: Path, stage: Path) -> None:
    required = [
        "awgn_smoke_frame_detail.csv", "awgn_smoke_summary.csv", "noise_reproducibility.csv",
        "noise_uniqueness.csv", "noise_scaling_audit.csv", "progress.jsonl", "plot_manifest.json",
        "figure_data_audit.csv", "bch12_smoke_ber.png", "bch12_smoke_fer.png",
        "bch12_smoke_true_success.png", "bch12_smoke_status.png",
    ]
    figure_data = sorted(results.glob("figure_data_bch12_*.csv"))
    for name in required:
        source = results / name
        if not source.is_file():
            raise SystemExit(f"missing BCH-12 artifact: {source}")
        shutil.copy2(source, stage / name)
    for source in figure_data:
        shutil.copy2(source, stage / source.name)
    forbidden = [path for path in results.rglob("*") if path.suffix.lower() in FORBIDDEN_PLOT_SUFFIXES]
    if forbidden:
        raise SystemExit("BLOCKED_BCH12_NON_PNG_PLOT")
    manifest = json.loads((stage / "plot_manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != 4:
        raise SystemExit("BCH-12 plot manifest must contain four PNGs")
    for item in manifest:
        path = stage / item["filename"]
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha256(path) != item["sha256"]:
            raise SystemExit("BCH-12 PNG hash or magic mismatch")

    progress_rows: list[dict[str, object]] = []
    latest: dict[tuple[str, float], dict[str, object]] = {}
    for line in (stage / "progress.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        latest[(row["caseName"], float(row["ebn0Db"]))] = row
    for key in sorted(latest):
        row = latest[key]
        progress_rows.append({"caseName": row["caseName"], "ebn0Db": row["ebn0Db"],
                              "processedFrames": row["processedFrames"], "status": row["status"],
                              "checkpointCount": row["checkpointCount"]})
    with (stage / "progress_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(progress_rows[0]))
        writer.writeheader(); writer.writerows(progress_rows)

    hash_rows: list[dict[str, object]] = []
    excluded = {"result_file_hashes.csv", "changes.patch", "manifest.json", "git_commit.txt"}
    for path in sorted(stage.iterdir()):
        if path.is_file() and path.name not in excluded:
            row_count = 0
            if path.suffix.lower() in {".csv", ".jsonl"}:
                row_count = max(0, len(path.read_text(encoding="utf-8").splitlines()) - (1 if path.suffix.lower() == ".csv" else 0))
            hash_rows.append({"path": path.name, "bytes": path.stat().st_size, "rowCount": row_count, "sha256": sha256(path)})
    with (stage / "result_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "rowCount", "sha256"])
        writer.writeheader(); writer.writerows(hash_rows)
    print(f"PASS_BCH12_ARTIFACT_PUBLISH files={len(hash_rows)} png=4 nonPngPlot=0")


def publish_bch13(results: Path, stage: Path) -> None:
    required = ["prescan_summary.csv", "prescan_case_recommendations.csv", "prescan_status_distribution.csv",
                "prescan_timing_summary.csv", "progress.jsonl", "plot_manifest.json", "figure_data_audit.csv",
                "bch13_prescan_200bit_ber.png", "bch13_prescan_200bit_fer.png",
                "bch13_prescan_300bit_ber.png", "bch13_prescan_300bit_fer.png",
                "bch13_prescan_miscorrection.png", "bch13_prescan_decode_time.png"]
    for name in required:
        source = results / name
        if not source.is_file(): raise SystemExit(f"missing BCH-13 artifact: {source}")
        shutil.copy2(source, stage / name)
    for source in sorted(results.glob("figure_data_bch13_*.csv")):
        shutil.copy2(source, stage / source.name)
    forbidden = [path for path in results.rglob("*") if path.suffix.lower() in FORBIDDEN_PLOT_SUFFIXES]
    if forbidden: raise SystemExit("BLOCKED_BCH13_NON_PNG_PLOT")
    manifest = json.loads((stage / "plot_manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != 6: raise SystemExit("BCH-13 plot manifest must contain six PNGs")
    for item in manifest:
        path = stage / item["filename"]
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha256(path) != item["sha256"]:
            raise SystemExit("BCH-13 PNG hash or magic mismatch")
    latest: dict[tuple[str, float], dict[str, object]] = {}
    for line in (stage / "progress.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line); latest[(row["caseName"], float(row["ebn0Db"]))] = row
    if len(latest) != 84 or any(row["status"] != "COMPLETE" for row in latest.values()):
        raise SystemExit("BCH-13 progress completion mismatch")
    progress_rows = [{"caseName": row["caseName"], "ebn0Db": row["ebn0Db"],
                      "processedFrames": row["processedFrames"], "status": row["status"]}
                     for _, row in sorted(latest.items())]
    with (stage / "progress_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(progress_rows[0])); writer.writeheader(); writer.writerows(progress_rows)
    excluded = {"result_file_hashes.csv", "changes.patch", "manifest.json", "git_commit.txt"}
    hash_rows = []
    for path in sorted(stage.iterdir()):
        if path.is_file() and path.name not in excluded:
            row_count = max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1) if path.suffix.lower() == ".csv" else 0
            hash_rows.append({"path": path.name, "bytes": path.stat().st_size, "rowCount": row_count, "sha256": sha256(path)})
    with (stage / "result_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "rowCount", "sha256"]); writer.writeheader(); writer.writerows(hash_rows)
    print(f"PASS_BCH13_ARTIFACT_PUBLISH files={len(hash_rows)} png=6 nonPngPlot=0")


def publish_bch14(results: Path, stage: Path) -> None:
    required = ["formal_trial_summary.csv", "resume_audit.csv", "shard_merge_audit.csv",
                "checkpoint_audit.csv", "negative_test_results.csv", "progress.jsonl"]
    for name in required:
        source = results / name
        if not source.is_file(): raise SystemExit(f"missing BCH-14 artifact: {source}")
        shutil.copy2(source, stage / name)
    latest: dict[tuple[str, str, float, int], dict[str, object]] = {}
    for line in (stage / "progress.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        latest[(row["stage"], row["caseName"], float(row["ebn0Db"]), int(row["shardIndex"]))] = row
    if len(latest) < 28 or any(row["status"] != "COMPLETE" for row in latest.values()):
        raise SystemExit("BCH-14 progress completion mismatch")
    progress_rows = [{"stage": row["stage"], "caseName": row["caseName"], "ebn0Db": row["ebn0Db"],
                      "shardIndex": row["shardIndex"], "shardCount": row["shardCount"],
                      "processedFrames": row["processedFrames"], "checkpointCount": row["checkpointCount"],
                      "status": row["status"]} for _, row in sorted(latest.items())]
    with (stage / "progress_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(progress_rows[0])); writer.writeheader(); writer.writerows(progress_rows)
    checkpoint_hash_rows = []
    for path in sorted(results.rglob("*.json")):
        if "checkpoints" in path.parts or path.name == "state.json":
            checkpoint_hash_rows.append({"path": str(path.relative_to(results)).replace("\\", "/"),
                                         "bytes": path.stat().st_size, "sha256": sha256(path)})
    with (stage / "checkpoint_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"]); writer.writeheader(); writer.writerows(checkpoint_hash_rows)
    excluded = {"result_file_hashes.csv", "changes.patch", "manifest.json", "git_commit.txt"}
    hash_rows = []
    for path in sorted(stage.iterdir()):
        if path.is_file() and path.name not in excluded:
            row_count = max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1) if path.suffix.lower() == ".csv" else 0
            hash_rows.append({"path": path.name, "bytes": path.stat().st_size, "rowCount": row_count, "sha256": sha256(path)})
    with (stage / "result_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "rowCount", "sha256"]); writer.writeheader(); writer.writerows(hash_rows)
    print(f"PASS_BCH14_ARTIFACT_PUBLISH files={len(hash_rows)} checkpoints={len(checkpoint_hash_rows)}")


def publish_bch15(results: Path, stage: Path) -> None:
    required = [
        "formal_summary.csv", "frozen_formal_grid.csv", "checkpoint_summary.csv",
        "progress.jsonl", "plot_manifest.json", "figure_data_audit.csv",
    ]
    expected_pngs = [
        "bch_200bit_ber_vs_ebn0.png", "bch_200bit_fer_vs_ebn0.png",
        "bch_200bit_true_success_vs_ebn0.png", "bch_200bit_reported_success_vs_ebn0.png",
        "bch_200bit_miscorrection_vs_ebn0.png", "bch_200bit_decode_time_vs_ebn0.png",
        "bch_300bit_ber_vs_ebn0.png", "bch_300bit_fer_vs_ebn0.png",
        "bch_300bit_true_success_vs_ebn0.png", "bch_300bit_reported_success_vs_ebn0.png",
        "bch_300bit_miscorrection_vs_ebn0.png", "bch_300bit_decode_time_vs_ebn0.png",
        "bch_all_cases_processed_frames.png", "bch_all_cases_stop_reason.png",
        "bch_decoder_status_distribution.png",
    ]
    for name in required + expected_pngs:
        source = results / name
        if not source.is_file():
            raise SystemExit(f"missing BCH-15 artifact: {source}")
        shutil.copy2(source, stage / name)
    for source in sorted(results.glob("figure_data_*.csv")):
        if source.name != "figure_data_audit.csv":
            shutil.copy2(source, stage / source.name)

    forbidden = [path for path in results.rglob("*") if path.suffix.lower() in FORBIDDEN_PLOT_SUFFIXES]
    if forbidden:
        raise SystemExit("BLOCKED_BCH15_NON_PNG_PLOT")
    manifest = json.loads((stage / "plot_manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != len(expected_pngs) or {item["filename"] for item in manifest} != set(expected_pngs):
        raise SystemExit("BCH-15 plot manifest does not match the 15 required PNGs")
    for item in manifest:
        path = stage / item["filename"]
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha256(path) != item["sha256"]:
            raise SystemExit("BCH-15 PNG hash or magic mismatch")

    with (stage / "formal_summary.csv").open(newline="", encoding="utf-8-sig") as handle:
        formal_rows = list(csv.DictReader(handle))
    with (stage / "frozen_formal_grid.csv").open(newline="", encoding="utf-8-sig") as handle:
        grid_rows = list(csv.DictReader(handle))
    formal_keys = {(row["caseName"], float(row["ebn0Db"])) for row in formal_rows}
    grid_keys = {(row["caseName"], float(row["ebn0Db"])) for row in grid_rows}
    if len(formal_rows) != 65 or len(formal_keys) != 65 or formal_keys != grid_keys:
        raise SystemExit("BLOCKED_BCH15_FORMAL_POINT_INCOMPLETE")

    latest: dict[tuple[str, float], dict[str, object]] = {}
    for line in (stage / "progress.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        latest[(row["caseName"], float(row["ebn0Db"]))] = row
    if set(latest) != formal_keys or any(row["status"] != "COMPLETE" for row in latest.values()):
        raise SystemExit("BCH-15 progress completion mismatch")
    progress_rows = [
        {"caseName": row["caseName"], "ebn0Db": row["ebn0Db"],
         "processedFrames": row["processedFrames"], "frameErrors": row["frameErrors"],
         "checkpointCount": row["checkpointCount"], "status": row["status"]}
        for _, row in sorted(latest.items())
    ]
    with (stage / "progress_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(progress_rows[0]))
        writer.writeheader(); writer.writerows(progress_rows)

    excluded = {"result_file_hashes.csv", "changes.patch", "manifest.json", "git_commit.txt"}
    hash_rows = []
    for path in sorted(stage.iterdir()):
        if path.is_file() and path.name not in excluded:
            row_count = 0
            if path.suffix.lower() == ".csv":
                row_count = max(0, len(path.read_text(encoding="utf-8-sig").splitlines()) - 1)
            elif path.suffix.lower() == ".jsonl":
                row_count = len(path.read_text(encoding="utf-8").splitlines())
            hash_rows.append({"path": path.name, "bytes": path.stat().st_size,
                              "rowCount": row_count, "sha256": sha256(path)})
    with (stage / "result_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "rowCount", "sha256"])
        writer.writeheader(); writer.writerows(hash_rows)
    print(f"PASS_BCH15_ARTIFACT_PUBLISH files={len(hash_rows)} png=15 nonPngPlot=0")


def publish_bch16(results: Path, stage: Path) -> None:
    expected_pngs = ["bch_200bit_rate_performance_comparison.png",
                     "bch_300bit_rate_performance_comparison.png",
                     "bch_decode_time_comparison.png", "bch_complexity_comparison.png"]
    required = ["comparison_summary.csv", "interpolation_audit.csv", "coding_gain_summary.csv",
                "complexity_comparison.csv", "recommendations.md", "plot_manifest.json",
                "figure_data_audit.csv"]
    for name in required + expected_pngs:
        source = results / name
        if not source.is_file(): raise SystemExit(f"missing BCH-16 artifact: {source}")
        shutil.copy2(source, stage / name)
    for source in sorted(results.glob("figure_data_*.csv")):
        if source.name != "figure_data_audit.csv": shutil.copy2(source, stage / source.name)
    forbidden = [path for path in results.rglob("*") if path.suffix.lower() in FORBIDDEN_PLOT_SUFFIXES]
    if forbidden: raise SystemExit("BLOCKED_BCH16_FIGURE_DATA_MISMATCH")
    manifest = json.loads((stage / "plot_manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != 4 or {item["filename"] for item in manifest} != set(expected_pngs):
        raise SystemExit("BCH-16 plot manifest mismatch")
    for item in manifest:
        path = stage / item["filename"]
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha256(path) != item["sha256"]:
            raise SystemExit("BLOCKED_BCH16_FIGURE_DATA_MISMATCH")
    with (stage / "comparison_summary.csv").open(newline="", encoding="utf-8-sig") as handle:
        comparisons = list(csv.DictReader(handle))
    with (stage / "interpolation_audit.csv").open(newline="", encoding="utf-8-sig") as handle:
        interpolations = list(csv.DictReader(handle))
    if len(comparisons) != 4 or len(interpolations) != 12:
        raise SystemExit("BLOCKED_BCH16_COMPARISON_INPUT_INCOMPLETE")
    invalid = [row for row in interpolations if row["interpolationValid"] == "false"]
    if len(invalid) != 2 or any(row["interpolatedEbN0"] for row in invalid):
        raise SystemExit("BLOCKED_BCH16_INVALID_INTERPOLATION")
    excluded = {"result_file_hashes.csv", "changes.patch", "manifest.json", "git_commit.txt"}
    hash_rows = []
    for path in sorted(stage.iterdir()):
        if path.is_file() and path.name not in excluded:
            row_count = max(0, len(path.read_text(encoding="utf-8-sig").splitlines()) - 1) if path.suffix.lower() == ".csv" else 0
            hash_rows.append({"path": path.name, "bytes": path.stat().st_size,
                              "rowCount": row_count, "sha256": sha256(path)})
    with (stage / "result_file_hashes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "rowCount", "sha256"])
        writer.writeheader(); writer.writerows(hash_rows)
    print(f"PASS_BCH16_ARTIFACT_PUBLISH files={len(hash_rows)} png=4 nonPngPlot=0")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["bch12", "bch13", "bch14", "bch15", "bch16"], required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()
    args.stage_dir.mkdir(parents=True, exist_ok=True)
    if args.stage == "bch12":
        publish_bch12(args.results_dir.resolve(), args.stage_dir.resolve())
    elif args.stage == "bch13":
        publish_bch13(args.results_dir.resolve(), args.stage_dir.resolve())
    elif args.stage == "bch14":
        publish_bch14(args.results_dir.resolve(), args.stage_dir.resolve())
    elif args.stage == "bch15":
        publish_bch15(args.results_dir.resolve(), args.stage_dir.resolve())
    else:
        publish_bch16(args.results_dir.resolve(), args.stage_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
