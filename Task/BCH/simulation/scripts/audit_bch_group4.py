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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["bch12"], required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    args = parser.parse_args()
    args.stage_dir.mkdir(parents=True, exist_ok=True)
    publish_bch12(args.results_dir.resolve(), args.stage_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
