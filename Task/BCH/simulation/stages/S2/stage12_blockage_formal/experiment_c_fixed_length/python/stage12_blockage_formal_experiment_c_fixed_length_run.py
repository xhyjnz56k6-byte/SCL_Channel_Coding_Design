import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[8]
EXPERIMENT = Path(__file__).resolve().parents[1]
STAGE = Path(__file__).resolve().parents[2]
BUILD = ROOT / "Task/BCH/simulation/build/S2/stage12_blockage_formal"
RESULTS = EXPERIMENT / "results"
LOGS = EXPERIMENT / "logs"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


def run(command, log_name):
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print(result.stdout, end="")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / log_name).write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.returncode)


config = json.loads(
    (EXPERIMENT / "configs/stage12_blockage_formal_experiment_c_fixed_length_config.json")
    .read_text(encoding="utf-8")
)
RESULTS.mkdir(parents=True, exist_ok=True)
points = RESULTS / "stage12_blockage_formal_experiment_c_fixed_length_points.csv"
with points.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow([
        "experimentType", "caseId", "ebn0Index", "ebn0Db",
        "blockageParameterIndex", "requestedBlockageLengthSymbols",
    ])
    lengths = config["fixedLengthExperiment"]["requestedBlockageLengthSymbols"]
    for case in CASES:
        family = "K200" if case.startswith("K200") else "K300"
        ebn0_db = config["fixedLengthExperiment"][family + "Ebn0Db"]
        for index, length in enumerate(lengths):
            writer.writerow(["FIXED_LENGTH", case, 0, ebn0_db, index, length])

run(
    ["cmake", "-S", str(STAGE / "cpp"), "-B", str(BUILD),
     "-G", "MinGW Makefiles", "-DCMAKE_BUILD_TYPE=Release"],
    "stage12_blockage_formal_experiment_c_fixed_length_cmake.log",
)
run(
    ["cmake", "--build", str(BUILD), "-j", "2"],
    "stage12_blockage_formal_experiment_c_fixed_length_build.log",
)
run(
    ["ctest", "--test-dir", str(BUILD), "-V", "--output-on-failure"],
    "stage12_blockage_formal_experiment_c_fixed_length_ctest.log",
)
git_commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
).strip()
run(
    [str(BUILD / "stage12_blockage_formal_runner.exe"), "--fixed-length",
     str(points), str(RESULTS), str(config["masterSeed"]), git_commit],
    "stage12_blockage_formal_experiment_c_fixed_length_runner.log",
)
run(
    ["python", str(EXPERIMENT / "python/stage12_blockage_formal_experiment_c_fixed_length_plot.py")],
    "stage12_blockage_formal_experiment_c_fixed_length_plot.log",
)
run(
    ["python", str(EXPERIMENT / "python/stage12_blockage_formal_experiment_c_fixed_length_checker.py")],
    "stage12_blockage_formal_experiment_c_fixed_length_checker.log",
)
