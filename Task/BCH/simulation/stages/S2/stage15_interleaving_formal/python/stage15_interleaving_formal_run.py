import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
BUILD_D = ROOT / "Task/BCH/simulation/build/S2/stage15_interleaving_formal_debug"
BUILD_R = ROOT / "Task/BCH/simulation/build/S2/stage15_interleaving_formal_release"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"
STAGE_ID = "stage15_interleaving_formal"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


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
    config_path = STAGE / f"configs/{STAGE_ID}_config.json"
    frozen_path = (
        STAGE13 / "results/stage13_burst_interleaving_validation_frozen_parameters.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        config_path.read_bytes() + b"\n" + frozen_path.read_bytes()
    ).hexdigest()
    return config, frozen, digest


def write_rows(path, fieldnames, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def permutation_sha():
    with (
        STAGE13 / "results/stage13_burst_interleaving_validation_permutation_sha256.csv"
    ).open(newline="", encoding="utf-8-sig") as stream:
        data = list(csv.DictReader(stream))
    return {
        (row["caseId"], row["interleaverMode"], int(row["interleaverDepth"])):
        row["permutationSha256"] for row in data
    }


def method_points(frozen):
    lookup = permutation_sha()
    data = []
    for case_id in CASES:
        payload = "200" if case_id.startswith("K200") else "300"
        for mode in ("BLOCK", "ROW_COLUMN", "PSEUDORANDOM"):
            for index, length in enumerate(
                frozen["stage15MethodBurstLengthsByPayload"][payload]
            ):
                data.append({
                    "caseId": case_id, "interleaverMode": mode,
                    "interleaverDepth": 8, "burstLengthIndex": index,
                    "burstLengthBits": length,
                    "permutationSha256": lookup[(case_id, mode, 8)],
                })
    path = RESULTS / f"{STAGE_ID}_method_points.csv"
    write_rows(path, list(data[0]), data)
    return path


def split(path, prefix, count=4):
    with path.open(newline="", encoding="utf-8") as stream:
        data = list(csv.DictReader(stream))
    paths = []
    for shard in range(count):
        shard_path = RESULTS / "shards" / f"{prefix}_shard_{shard}_points.csv"
        write_rows(shard_path, list(data[0]), data[shard::count])
        paths.append(shard_path)
    return paths


def run_shards(paths, prefix, config, config_hash, commit):
    stop = config["stopRule"]
    checkpoints = RESULTS / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    processes = []
    for shard, path in enumerate(paths):
        output = RESULTS / "shards" / f"{prefix}_shard_{shard}_results.csv"
        command = [
            BUILD_R / f"{STAGE_ID}_runner.exe", path, output, checkpoints,
            config["masterSeed"], config["interleaverSeed"], config_hash,
            commit, stop["minFrames"], stop["targetFrameErrors"],
            stop["maxFrames"], stop["checkpointIntervalFrames"],
        ]
        process = subprocess.Popen(
            [str(value) for value in command], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        processes.append((shard, process, command))
    for shard, process, command in processes:
        output, _ = process.communicate()
        print(output, end="")
        (LOGS / f"{prefix}_shard_{shard}.log").write_text(
            output, encoding="utf-8"
        )
        if process.returncode:
            raise SystemExit(
                f"shard failed: {' '.join(str(x) for x in command)}"
            )


def matlab_path(path):
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def run_matlab():
    cpp = (
        STAGE13 / "results/stage13_burst_interleaving_validation_cpp_outputs.csv"
    )
    permutations = (
        STAGE13 / "results/stage13_burst_interleaving_validation_permutations.csv"
    )
    output = RESULTS / f"{STAGE_ID}_matlab_comparison.csv"
    command = (
        f"addpath('{matlab_path(STAGE / 'matlab')}'); "
        "stage15_interleaving_formal_matlab_reference("
        f"'{matlab_path(cpp)}','{matlab_path(permutations)}',"
        f"'{matlab_path(output)}',"
        f"'{matlab_path(ROOT / 'Task/BCH/segmented/matlab')}',"
        f"'{matlab_path(STAGE13 / 'matlab')}');"
    )
    run(["matlab", "-batch", command], LOGS / f"{STAGE_ID}_matlab.log")


def smoke(config, config_hash):
    output = RESULTS / "smoke" / f"{STAGE_ID}_smoke_results.csv"
    run(
        [
            BUILD_R / f"{STAGE_ID}_runner.exe",
            STAGE / f"tests/{STAGE_ID}_smoke_points.csv", output,
            RESULTS / "smoke/checkpoints", config["masterSeed"],
            config["interleaverSeed"], config_hash,
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            10, 2, 50, 10,
        ],
        LOGS / f"{STAGE_ID}_smoke.log",
    )
    print("PASS_STAGE15_INTERLEAVING_FORMAL_SMOKE")


def formal(config, frozen, config_hash):
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    allowed = (
        "Task/BCH/simulation/stages/S2/stage15_interleaving_formal/results/logs/"
    )
    dirty = [
        line[3:].replace("\\", "/") for line in status.splitlines() if line.strip()
    ]
    if any(not path.startswith(allowed) for path in dirty):
        raise SystemExit("Stage15 formal source/config/test files are not clean")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    method = method_points(frozen)
    run_shards(split(method, f"{STAGE_ID}_method"), f"{STAGE_ID}_method",
               config, config_hash, commit)
    run(
        ["python", STAGE / f"python/{STAGE_ID}_finalize.py",
         "--select", "--git-commit", commit],
        LOGS / f"{STAGE_ID}_selection.log",
    )
    depth = RESULTS / f"{STAGE_ID}_depth_points.csv"
    run_shards(split(depth, f"{STAGE_ID}_depth"), f"{STAGE_ID}_depth",
               config, config_hash, commit)
    run(
        ["python", STAGE / f"python/{STAGE_ID}_finalize.py",
         "--finalize", "--git-commit", commit],
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
    config, frozen, config_hash = load_config()
    build()
    if args.formal:
        formal(config, frozen, config_hash)
    else:
        smoke(config, config_hash)


if __name__ == "__main__":
    main()

