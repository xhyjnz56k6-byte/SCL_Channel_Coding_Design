#!/usr/bin/env python3
"""Run remaining BCH-16V point jobs in balanced independent MATLAB processes."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path


FILES = [
    "matlab_official_formal_summary.csv",
    "official_representative_decode_summary.csv",
    "paired_frame_error_contingency.csv",
]


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, values: list[dict[str, str]]) -> None:
    if not values:
        raise RuntimeError(f"no rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def matlab_quote(value: Path | str) -> str:
    return str(value).replace("\\", "/").replace("'", "''")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab", required=True)
    parser.add_argument("--matlab-dir", required=True, type=Path)
    parser.add_argument("--runtime-config", required=True, type=Path)
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    manifest = json.loads(args.input_manifest.read_text(encoding="utf-8"))
    base_config = json.loads(args.runtime_config.read_text(encoding="utf-8"))
    main_results = args.results_dir
    existing = {name: rows(main_results / name) for name in FILES}
    completed = {(row["caseName"], int(row["snrIndex"])) for row in existing[FILES[0]]}
    remaining = [(index + 1, point) for index, point in enumerate(manifest["points"])
                 if (point["caseName"], int(point["snrIndex"])) not in completed]
    if not remaining:
        print("PASS_BCH16V_MATLAB_PARALLEL no remaining points")
        return 0
    worker_count = min(args.workers, len(remaining))
    assignments: list[list[tuple[int, dict[str, object]]]] = [[] for _ in range(worker_count)]
    loads = [0] * worker_count
    for item in sorted(remaining, key=lambda value: int(value[1]["processedFrames"]), reverse=True):
        target = min(range(worker_count), key=loads.__getitem__)
        assignments[target].append(item)
        loads[target] += int(item[1]["processedFrames"])
    print("BCH-16V parallel MATLAB plan")
    for index, assignment in enumerate(assignments):
        print(f"worker {index}: points={[item[0] for item in assignment]} frames={loads[index]}")

    processes: list[tuple[int, subprocess.Popen[str], object]] = []
    worker_root = main_results.parent / "matlab_workers"
    worker_root.mkdir(parents=True, exist_ok=True)
    for index, assignment in enumerate(assignments):
        worker_dir = worker_root / f"worker_{index}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        config = dict(base_config)
        config["pointIndices"] = [item[0] for item in assignment]
        config_path = worker_dir / "runtime_config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        log = (worker_dir / "matlab.log").open("w", encoding="utf-8")
        expression = (
            f"addpath('{matlab_quote(args.matlab_dir)}');"
            f"run_bch16v_official_awgn('{matlab_quote(config_path)}','{matlab_quote(args.input_manifest)}',"
            f"'{matlab_quote(worker_dir)}',false)"
        )
        process = subprocess.Popen([args.matlab, "-batch", expression], stdout=log, stderr=subprocess.STDOUT, text=True)
        processes.append((index, process, log))
    pending = {index for index, _, _ in processes}
    while pending:
        time.sleep(10)
        for index, process, _ in processes:
            if index in pending and process.poll() is not None:
                pending.remove(index)
                print(f"worker {index} exit={process.returncode}", flush=True)
    failures = []
    for index, process, log in processes:
        log.close()
        if process.returncode:
            failures.append(index)
    if failures:
        for index in failures:
            print((worker_root / f"worker_{index}/matlab.log").read_text(encoding="utf-8", errors="replace")[-4000:])
        raise SystemExit("BLOCKED_BCH16V_MATLAB_WORKER_FAILURE")

    order = {(point["caseName"], int(point["snrIndex"])): index for index, point in enumerate(manifest["points"])}
    for name in FILES:
        combined = list(existing[name])
        for index in range(worker_count):
            combined.extend(rows(worker_root / f"worker_{index}" / name))
        keys = [(row["caseName"], int(row["snrIndex"])) for row in combined]
        if len(keys) != len(set(keys)) or len(keys) != len(manifest["points"]):
            raise SystemExit("BLOCKED_BCH16V_MISSING_FORMAL_POINT")
        combined.sort(key=lambda row: order[(row["caseName"], int(row["snrIndex"]))])
        write_rows(main_results / name, combined)
    for name in ("matlab_environment.json", "official_parameter_audit.csv",
                 "official_encoding_compare_summary.csv", "official_encoding_compare_detail.csv"):
        shutil.copy2(worker_root / "worker_0" / name, main_results / name)
    print(f"PASS_BCH16V_MATLAB_PARALLEL points={len(manifest['points'])} workers={worker_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
