import csv
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task/BCH/simulation/build/S2/stage12_blockage_formal"
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


def run(command, log_name):
    result = subprocess.run(command, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end="")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / log_name).write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.returncode)


if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
    raise SystemExit("BLOCKED_DIRTY_WORKTREE_FORMAL_RUN")

config = json.loads((STAGE / "configs/stage12_blockage_formal_config.json").read_text(encoding="utf-8"))
RESULTS.mkdir(parents=True, exist_ok=True)
old_summary = RESULTS / "stage12_blockage_formal_result_summary.csv"
old_raw = RESULTS / "stage12_blockage_formal_result_raw.csv"
old_points = RESULTS / "stage12_blockage_formal_points.csv"
old_merge = RESULTS / "stage12_blockage_formal_merge_audit.csv"
with old_summary.open(encoding="utf-8", newline="") as stream:
    old_summary_rows = list(csv.DictReader(stream))
old_a_summary = [row for row in old_summary_rows if row["experimentType"] == "RATIO"]
if len(old_a_summary) != 64:
    raise SystemExit("BLOCKED_STAGE12_A_BASELINE_NOT_64_POINTS")
with old_raw.open(encoding="utf-8", newline="") as stream:
    old_raw_rows = list(csv.DictReader(stream))
old_a_raw = [row for row in old_raw_rows if row["experimentType"] == "RATIO"]
with old_points.open(encoding="utf-8", newline="") as stream:
    old_point_rows = list(csv.DictReader(stream))
old_a_points = [row for row in old_point_rows if row["experimentType"] == "RATIO"]
with old_merge.open(encoding="utf-8", newline="") as stream:
    old_merge_rows = list(csv.DictReader(stream))
old_a_merge = [row for row in old_merge_rows if row["experimentType"] == "RATIO"]

run(["cmake", "-S", str(STAGE / "cpp"), "-B", str(BUILD), "-G", "MinGW Makefiles",
     "-DCMAKE_BUILD_TYPE=Release"], "stage12_blockage_formal_cmake.log")
run(["cmake", "--build", str(BUILD), "-j", "2"], "stage12_blockage_formal_build.log")
run(["ctest", "--test-dir", str(BUILD), "-V", "--output-on-failure"],
    "stage12_blockage_formal_ctest.log")

commit = subprocess.check_output([
    "git", "log", "-n", "1", "--format=%H", "--",
    "Task/BCH/simulation/stages/S2/stage12_blockage_formal/cpp/stage12_blockage_formal_runner.cpp"
], cwd=ROOT, text=True).strip()
rates = {row["caseId"]: float(row["actualRate"]) for row in old_summary_rows}
grid = config["snrExperiment"]["targetSnrDb"]
work = RESULTS / "dense_snr_experiment_b"
work.mkdir(parents=True, exist_ok=True)
b_points = work / "stage12_blockage_formal_experiment_b_dense_snr_points.csv"
with b_points.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["experimentType", "caseId", "ebn0Index", "ebn0Db",
                     "blockageParameterIndex", "requestedBlockageRatio", "targetSnrDb"])
    for case in CASES:
        rate = rates[case]
        for index, target in enumerate(grid):
            writer.writerow(["SNR", case, index, target - 10 * math.log10(rate),
                             index, config["snrExperiment"]["representativeRatio"], target])
run([str(BUILD / "stage12_blockage_formal_runner.exe"), str(b_points), str(work),
     str(config["masterSeed"]), commit], "stage12_blockage_formal_dense_snr_b_runner.log")

new_raw = work / "stage12_blockage_formal_result_raw.csv"
new_summary = work / "stage12_blockage_formal_result_summary.csv"
new_merge = work / "stage12_blockage_formal_merge_audit.csv"
with new_raw.open(encoding="utf-8", newline="") as stream:
    b_raw = list(csv.DictReader(stream))
with new_summary.open(encoding="utf-8", newline="") as stream:
    b_summary = list(csv.DictReader(stream))
if len(b_summary) != 136:
    raise SystemExit("BLOCKED_STAGE12_DENSE_SNR_B_POINT_COUNT")
with new_merge.open(encoding="utf-8", newline="") as stream:
    b_merge = list(csv.DictReader(stream))

def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

write_rows(old_raw, old_a_raw + b_raw)
write_rows(old_summary, old_a_summary + b_summary)
write_rows(RESULTS / "stage12_blockage_formal_merge_audit.csv", old_a_merge + b_merge)

point_fields = ["experimentType", "caseId", "ebn0Index", "ebn0Db",
                "blockageParameterIndex", "requestedBlockageRatio", "targetSnrDb"]
canonical_points = []
for row in old_a_points:
    target = float(row["ebn0Db"]) + 10 * math.log10(rates[row["caseId"]])
    canonical_points.append({**row, "targetSnrDb": f"{target:.17g}"})
with b_points.open(encoding="utf-8", newline="") as stream:
    canonical_points.extend(dict(row) for row in csv.DictReader(stream))
with old_points.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=point_fields)
    writer.writeheader()
    writer.writerows(canonical_points)

run(["python", str(STAGE / "python/stage12_blockage_formal_plot.py")],
    "stage12_blockage_formal_plot.log")
run(["python", str(STAGE / "python/stage12_blockage_formal_checker.py")],
    "stage12_blockage_formal_checker.log")
run(["python", str(STAGE / "python/stage12_blockage_formal_matlab_spotcheck.py")],
    "stage12_blockage_formal_matlab_runner.log")
