import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD_DEBUG = ROOT / "Task/BCH/simulation/build/S2/stage13_burst_interleaving_validation_debug"
BUILD_RELEASE = ROOT / "Task/BCH/simulation/build/S2/stage13_burst_interleaving_validation_release"
RESULTS = STAGE / "results"
LOGS = RESULTS / "logs"


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


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config_path = (
        STAGE
        / "configs/stage13_burst_interleaving_validation_config.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))

    run(
        [
            "cmake",
            "-S",
            STAGE / "cpp",
            "-B",
            BUILD_DEBUG,
            "-G",
            "MinGW Makefiles",
            "-DCMAKE_BUILD_TYPE=Debug",
        ],
        LOGS / "stage13_burst_interleaving_validation_cmake_debug.log",
    )
    run(
        ["cmake", "--build", BUILD_DEBUG, "-j", "2"],
        LOGS / "stage13_burst_interleaving_validation_build_debug.log",
    )
    run(
        [
            "ctest",
            "--test-dir",
            BUILD_DEBUG,
            "--output-on-failure",
            "-V",
        ],
        LOGS / "stage13_burst_interleaving_validation_ctest.log",
    )
    run(
        [
            "cmake",
            "-S",
            STAGE / "cpp",
            "-B",
            BUILD_RELEASE,
            "-G",
            "MinGW Makefiles",
            "-DCMAKE_BUILD_TYPE=Release",
        ],
        LOGS / "stage13_burst_interleaving_validation_cmake_release.log",
    )
    run(
        ["cmake", "--build", BUILD_RELEASE, "-j", "2"],
        LOGS / "stage13_burst_interleaving_validation_build_release.log",
    )
    run(
        [
            BUILD_RELEASE
            / "stage13_burst_interleaving_validation_runner.exe",
            RESULTS,
            config["masterSeed"],
            config["interleaverSeed"],
        ],
        LOGS / "stage13_burst_interleaving_validation_runner.log",
    )

    cpp_csv = (
        RESULTS
        / "stage13_burst_interleaving_validation_cpp_outputs.csv"
    )
    permutations = (
        RESULTS
        / "stage13_burst_interleaving_validation_permutations.csv"
    )
    matlab_csv = (
        RESULTS
        / "stage13_burst_interleaving_validation_matlab_outputs.csv"
    )
    segmented_reference = ROOT / "Task/BCH/segmented/matlab"
    matlab_script = STAGE / "matlab"
    matlab_command = (
        f"addpath('{matlab_path(matlab_script)}'); "
        "stage13_burst_interleaving_validation_matlab_reference("
        f"'{matlab_path(cpp_csv)}','{matlab_path(permutations)}',"
        f"'{matlab_path(matlab_csv)}',"
        f"'{matlab_path(segmented_reference)}');"
    )
    run(
        ["matlab", "-batch", matlab_command],
        LOGS / "stage13_burst_interleaving_validation_matlab.log",
    )
    run(
        [
            "python",
            STAGE
            / "python/stage13_burst_interleaving_validation_check.py",
        ],
        LOGS / "stage13_burst_interleaving_validation_check.log",
    )

    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    print(
        "stage13 config sha256="
        + config_hash
    )


if __name__ == "__main__":
    main()

