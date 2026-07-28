import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
BUILD_D = ROOT / "Task/BCH/simulation/build/S2/s16_bic_d"
BUILD_R = ROOT / "Task/BCH/simulation/build/S2/s16_bic_r"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage16_burst_interleaving_comparison"


def run(command, log):
    result = subprocess.run(
        [str(value) for value in command], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    print(result.stdout, end="")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(
            f"command failed ({result.returncode}): "
            + " ".join(str(value) for value in command)
        )


def build():
    for directory, kind in ((BUILD_D, "Debug"), (BUILD_R, "Release")):
        run(
            ["cmake", "-S", STAGE / "cpp", "-B", directory,
             "-G", "MinGW Makefiles", f"-DCMAKE_BUILD_TYPE={kind}"],
            LOGS / f"{STAGE_ID}_cmake_{kind.lower()}.log",
        )
        run(
            ["cmake", "--build", directory, "-j", "2"],
            LOGS / f"{STAGE_ID}_build_{kind.lower()}.log",
        )
    run(
        ["ctest", "--test-dir", BUILD_D, "--output-on-failure", "-V"],
        LOGS / f"{STAGE_ID}_ctest.log",
    )


def load_config():
    path = STAGE / f"configs/{STAGE_ID}_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return config, digest


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def split(path, count=4):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    paths = []
    for shard in range(count):
        target = RESULTS / "shards" / f"{STAGE_ID}_shard_{shard}_points.csv"
        write(target, rows[shard::count])
        paths.append(target)
    return paths


def run_shards(paths, config, digest, commit):
    stop = config["stopRule"]
    checkpoints = RESULTS / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    processes = []
    for shard, points in enumerate(paths):
        output = RESULTS / "shards" / f"{STAGE_ID}_shard_{shard}_results.csv"
        command = [
            BUILD_R / f"{STAGE_ID}_runner.exe", points, output, checkpoints,
            config["masterSeed"], config["interleaverSeed"], digest, commit,
            stop["minFrames"], stop["targetFrameErrors"], stop["maxFrames"],
            stop["checkpointIntervalFrames"],
        ]
        process = subprocess.Popen(
            [str(value) for value in command], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        processes.append((shard, process, command))
    for shard, process, command in processes:
        output, _ = process.communicate()
        print(output, end="")
        (LOGS / f"{STAGE_ID}_shard_{shard}.log").write_text(
            output, encoding="utf-8"
        )
        if process.returncode:
            raise SystemExit(
                f"Stage16 shard failed: {' '.join(str(x) for x in command)}"
            )


def matlab_path(path):
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def run_matlab():
    vector_output = RESULTS / f"{STAGE_ID}_matlab_vector_comparison.csv"
    snr_output = RESULTS / f"{STAGE_ID}_matlab_snr_comparison.csv"
    command = (
        f"addpath('{matlab_path(STAGE / 'matlab')}'); "
        f"{STAGE_ID}_matlab_reference("
        f"'{matlab_path(STAGE13 / 'results/stage13_burst_interleaving_validation_cpp_outputs.csv')}',"
        f"'{matlab_path(STAGE13 / 'results/stage13_burst_interleaving_validation_permutations.csv')}',"
        f"'{matlab_path(RESULTS / f'{STAGE_ID}_points.csv')}',"
        f"'{matlab_path(vector_output)}','{matlab_path(snr_output)}',"
        f"'{matlab_path(ROOT / 'Task/BCH/segmented/matlab')}',"
        f"'{matlab_path(STAGE13 / 'matlab')}');"
    )
    run(["matlab", "-batch", command], LOGS / f"{STAGE_ID}_matlab.log")


def smoke(config, digest):
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    run(
        [
            BUILD_R / f"{STAGE_ID}_runner.exe",
            STAGE / f"tests/{STAGE_ID}_smoke_points.csv",
            RESULTS / "smoke" / f"{STAGE_ID}_smoke_results.csv",
            RESULTS / "smoke/checkpoints",
            config["masterSeed"], config["interleaverSeed"], digest, commit,
            10, 2, 50, 10,
        ],
        LOGS / f"{STAGE_ID}_smoke.log",
    )
    print("PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_SMOKE")


def formal(config, digest):
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    allowed = (
        "Task/BCH/simulation/stages/S2/"
        "stage16_burst_interleaving_comparison/results/logs/"
    )
    dirty = [
        line[3:].replace("\\", "/") for line in status.splitlines() if line.strip()
    ]
    if any(not path.startswith(allowed) for path in dirty):
        raise SystemExit("Stage16 formal source/config/test files are not clean")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    run(
        ["python", STAGE / f"python/{STAGE_ID}_prepare.py"],
        LOGS / f"{STAGE_ID}_prepare.log",
    )
    run_shards(split(RESULTS / f"{STAGE_ID}_points.csv"), config, digest, commit)
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
    config, digest = load_config()
    build()
    if args.formal:
        formal(config, digest)
    else:
        smoke(config, digest)


if __name__ == "__main__":
    main()
