import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
BUILD_DEBUG = ROOT / "Task/BCH/simulation/build/S2/stage14_burst_formal_debug"
BUILD_RELEASE = ROOT / "Task/BCH/simulation/build/S2/stage14_burst_formal_release"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage14_burst_formal"
CASE_ORDER = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


def run(command, log_path):
    result = subprocess.run(
        [str(value) for value in command],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout, end="")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(
            f"command failed ({result.returncode}): "
            + " ".join(str(value) for value in command)
        )


def matlab_path(path):
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def build_and_test():
    run(
        [
            "cmake", "-S", STAGE / "cpp", "-B", BUILD_DEBUG,
            "-G", "MinGW Makefiles", "-DCMAKE_BUILD_TYPE=Debug",
        ],
        LOGS / f"{STAGE_ID}_cmake_debug.log",
    )
    run(
        ["cmake", "--build", BUILD_DEBUG, "-j", "2"],
        LOGS / f"{STAGE_ID}_build_debug.log",
    )
    run(
        ["ctest", "--test-dir", BUILD_DEBUG, "--output-on-failure", "-V"],
        LOGS / f"{STAGE_ID}_ctest.log",
    )
    run(
        [
            "cmake", "-S", STAGE / "cpp", "-B", BUILD_RELEASE,
            "-G", "MinGW Makefiles", "-DCMAKE_BUILD_TYPE=Release",
        ],
        LOGS / f"{STAGE_ID}_cmake_release.log",
    )
    run(
        ["cmake", "--build", BUILD_RELEASE, "-j", "2"],
        LOGS / f"{STAGE_ID}_build_release.log",
    )


def config_and_frozen():
    config_path = STAGE / f"configs/{STAGE_ID}_config.json"
    frozen_path = (
        STAGE13
        / "results/stage13_burst_interleaving_validation_frozen_parameters.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        config_path.read_bytes() + b"\n" + frozen_path.read_bytes()
    ).hexdigest()
    return config, frozen, digest


def write_points(frozen):
    path = RESULTS / f"{STAGE_ID}_points.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["caseId", "burstLengthIndex", "burstLengthBits"])
        for case_id in CASE_ORDER:
            payload = "200" if case_id.startswith("K200") else "300"
            for index, length in enumerate(
                frozen["stage14BurstLengthsByPayload"][payload]
            ):
                writer.writerow([case_id, index, length])
    return path


def run_smoke(config, config_hash):
    smoke = RESULTS / "smoke"
    smoke.mkdir(parents=True, exist_ok=True)
    run(
        [
            BUILD_RELEASE / f"{STAGE_ID}_runner.exe",
            STAGE / f"tests/{STAGE_ID}_smoke_points.csv",
            smoke / f"{STAGE_ID}_smoke_results.csv",
            smoke / "checkpoints",
            config["masterSeed"],
            config_hash,
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            10, 2, 50, 10,
        ],
        LOGS / f"{STAGE_ID}_smoke.log",
    )
    print("PASS_STAGE14_BURST_FORMAL_SMOKE")


def split_points(points_path, shard_count):
    with points_path.open(newline="", encoding="utf-8") as stream:
        reader = list(csv.reader(stream))
    header, rows = reader[0], reader[1:]
    shard_dir = RESULTS / "shards"
    shard_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for shard_id in range(shard_count):
        path = shard_dir / f"{STAGE_ID}_shard_{shard_id}_points.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows[shard_id::shard_count])
        paths.append(path)
    return paths


def run_shards(point_shards, config, config_hash, git_commit):
    checkpoints = RESULTS / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    stop = config["stopRule"]
    processes = []
    result_paths = []
    for shard_id, point_path in enumerate(point_shards):
        result_path = (
            RESULTS / "shards" / f"{STAGE_ID}_shard_{shard_id}_results.csv"
        )
        command = [
            BUILD_RELEASE / f"{STAGE_ID}_runner.exe",
            point_path,
            result_path,
            checkpoints,
            config["masterSeed"],
            config_hash,
            git_commit,
            stop["minFrames"],
            stop["targetFrameErrors"],
            stop["maxFrames"],
            stop["checkpointIntervalFrames"],
        ]
        process = subprocess.Popen(
            [str(value) for value in command],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append((shard_id, process, command))
        result_paths.append(result_path)
    for shard_id, process, command in processes:
        output, _ = process.communicate()
        print(output, end="")
        log = LOGS / f"{STAGE_ID}_shard_{shard_id}.log"
        log.write_text(output, encoding="utf-8")
        if process.returncode:
            raise SystemExit(
                f"shard {shard_id} failed ({process.returncode}): "
                + " ".join(str(value) for value in command)
            )
    return result_paths


def merge_shards(result_paths):
    header = None
    rows = []
    for path in result_paths:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            shard_header = next(reader)
            if header is None:
                header = shard_header
            elif shard_header != header:
                raise SystemExit("Stage14 shard headers differ")
            rows.extend(reader)
    case_index = {case_id: index for index, case_id in enumerate(CASE_ORDER)}
    case_column = header.index("caseId")
    length_column = header.index("burstLengthBits")
    rows.sort(
        key=lambda row: (
            case_index[row[case_column]],
            int(row[length_column]),
        )
    )
    path = RESULTS / f"{STAGE_ID}_raw_results.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def run_matlab():
    samples = RESULTS / f"{STAGE_ID}_matlab_samples.csv"
    output = RESULTS / f"{STAGE_ID}_matlab_comparison.csv"
    script_directory = STAGE / "matlab"
    segmented = ROOT / "Task/BCH/segmented/matlab"
    command = (
        f"addpath('{matlab_path(script_directory)}'); "
        "stage14_burst_formal_matlab_reference("
        f"'{matlab_path(samples)}','{matlab_path(output)}',"
        f"'{matlab_path(segmented)}');"
    )
    run(
        ["matlab", "-batch", command],
        LOGS / f"{STAGE_ID}_matlab.log",
    )


def run_formal(config, frozen, config_hash):
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    dirty_paths = [
        line[3:].replace("\\", "/")
        for line in status.splitlines()
        if line.strip()
    ]
    allowed_log_prefix = (
        "Task/BCH/simulation/stages/S2/stage14_burst_formal/results/logs/"
    )
    if any(
        not path.startswith(allowed_log_prefix) for path in dirty_paths
    ):
        raise SystemExit(
            "formal run requires immutable source/config/test files; "
            "only current Stage14 build logs may be dirty"
        )
    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    points = write_points(frozen)
    point_shards = split_points(points, 4)
    result_paths = run_shards(
        point_shards, config, config_hash, git_commit
    )
    merge_shards(result_paths)
    run(
        ["python", STAGE / f"python/{STAGE_ID}_finalize.py"],
        LOGS / f"{STAGE_ID}_finalize.log",
    )
    run_matlab()
    run(
        ["python", STAGE / f"python/{STAGE_ID}_plot.py"],
        LOGS / f"{STAGE_ID}_plot.log",
    )
    run(
        ["python", STAGE / f"python/{STAGE_ID}_check.py"],
        LOGS / f"{STAGE_ID}_check.log",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config, frozen, config_hash = config_and_frozen()
    build_and_test()
    if args.formal:
        run_formal(config, frozen, config_hash)
    else:
        run_smoke(config, config_hash)


if __name__ == "__main__":
    main()
