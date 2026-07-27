import csv
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task/BCH/simulation/build/S2/stage07_awgn_dense_formal"
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"
PUBLISHED = STAGE / "published_results"
CONFIG = STAGE / "configs/stage07_awgn_dense_formal_config.json"
CASE_CONTRACT = ROOT / "Task/BCH/simulation/stages/S2/stage02_case_contract/results/stage02_case_contract_cases.csv"


def run(command, log=None):
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end="")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(map(str, command))}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cases():
    with CASE_CONTRACT.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def snr_grid(config):
    grid = config["waveformSnrGridDb"]
    values = []
    x = float(grid["start"])
    stop = float(grid["stop"])
    step = float(grid["step"])
    while x <= stop + 1e-12:
        values.append(round(x, 10))
        x += step
    return values


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_frozen_files(config, cases, grid):
    rows = []
    for case in cases:
        rate = float(case["actualRate"])
        for index, snr_db in enumerate(grid):
            ebn0_db = snr_db - 10.0 * math.log10(2.0 * rate)
            sigma2 = 1.0 / (10.0 ** (snr_db / 10.0))
            rows.append({
                "caseId": case["caseId"],
                "snrIndex": index,
                "snrDb": f"{snr_db:.1f}",
                "actualRate": f"{rate:.17g}",
                "ebn0Db": f"{ebn0_db:.17g}",
                "sigma2": f"{sigma2:.17g}",
            })
    write_csv(STAGE / "stage07_awgn_dense_formal_frozen_grid.csv", rows,
              ["caseId", "snrIndex", "snrDb", "actualRate", "ebn0Db", "sigma2"])
    config_rows = [{
        "stageId": config["stageId"],
        "masterSeed": config["masterSeed"],
        "snrStartDb": config["waveformSnrGridDb"]["start"],
        "snrStopDb": config["waveformSnrGridDb"]["stop"],
        "snrStepDb": config["waveformSnrGridDb"]["step"],
        "snrInclusive": config["waveformSnrGridDb"]["inclusive"],
        "minFrames": config["stopRule"]["minFrames"],
        "targetFrameErrors": config["stopRule"]["targetFrameErrors"],
        "maxFrames": config["stopRule"]["maxFrames"],
        "checkpointEveryFrames": config["checkpointEveryFrames"],
    }]
    write_csv(STAGE / "stage07_awgn_dense_formal_frozen_config.csv", config_rows,
              list(config_rows[0].keys()))


def write_points(cases, grid):
    rows = []
    for case in cases:
        for index, snr_db in enumerate(grid):
            rows.append({"caseId": case["caseId"], "snrIndex": index, "snrDb": f"{snr_db:.1f}"})
    points = RESULTS / "stage07_awgn_dense_formal_points.csv"
    write_csv(points, rows, ["caseId", "snrIndex", "snrDb"])
    return points


def publish_small_results():
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    for name in (
        "stage07_awgn_dense_formal_results.csv",
        "stage07_awgn_dense_formal_summary.csv",
        "stage07_awgn_dense_formal_stop_reason_summary.csv",
        "stage07_awgn_dense_formal_point_audit.csv",
        "stage07_awgn_dense_formal_raw_results_manifest.json",
    ):
        src = RESULTS / name
        if src.exists():
            shutil.copy2(src, PUBLISHED / name)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cases = read_cases()
    grid = snr_grid(config)
    write_frozen_files(config, cases, grid)
    points = write_points(cases, grid)
    config_hash = sha(CONFIG)
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run(["cmake", "-S", str(STAGE / "cpp"), "-B", str(BUILD), "-G", "MinGW Makefiles",
         "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", str(BUILD), "--config", "Release", "-j", "2"])
    run(["ctest", "--test-dir", str(BUILD), "-C", "Release", "--output-on-failure", "-V"],
        LOGS / "stage07_awgn_dense_formal_ctest.log")
    runner = BUILD / "stage07_awgn_dense_formal_runner.exe"
    run([str(runner), "--resume-test", str(RESULTS), str(config["masterSeed"]), config_hash, git_commit],
        LOGS / "stage07_awgn_dense_formal_resume_test.log")
    run([str(runner), str(points), str(RESULTS), str(config["masterSeed"]), config_hash, git_commit],
        LOGS / "stage07_awgn_dense_formal_runner.log")
    run(["python", str(STAGE / "python/stage07_awgn_dense_formal_plot.py")],
        LOGS / "stage07_awgn_dense_formal_plot.log")
    run(["python", str(STAGE / "python/stage07_awgn_dense_formal_check.py")],
        LOGS / "stage07_awgn_dense_formal_check.log")
    publish_small_results()


if __name__ == "__main__":
    main()
