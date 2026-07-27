import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task" / "BCH" / "simulation" / "build" / "S2" / "stage05_awgn_trial"
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"


def run(command, log=None):
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    print(result.stdout, end="")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(map(str, command))}")


def stop_decision(frames, errors):
    if frames >= 5000 and errors >= 200:
        return "TARGET_FRAME_ERRORS_REACHED"
    if frames >= 50000:
        return "MAX_FRAMES_REACHED"
    return "CONTINUE"


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config = json.loads((STAGE / "configs" / "stage05_awgn_trial_config.json").read_text(encoding="utf-8"))
    points_path = RESULTS / "stage05_awgn_trial_points.csv"
    with points_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["caseId", "ebn0Index", "ebn0Db"])
        for case_id, points in config["points"].items():
            for index, ebn0_db in enumerate(points):
                writer.writerow([case_id, index, ebn0_db])
    stop_path = RESULTS / "stage05_awgn_trial_formal_stop_rule_test.csv"
    with stop_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["totalFrames", "payloadErrorFrames", "decision"])
        for frames, errors in ((4999, 200), (5000, 200), (5000, 199), (50000, 199)):
            writer.writerow([frames, errors, stop_decision(frames, errors)])

    run(["cmake", "-S", str(STAGE / "cpp"), "-B", str(BUILD), "-G", "MinGW Makefiles",
         "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", str(BUILD), "--config", "Release", "-j", "2"])
    run(["ctest", "--test-dir", str(BUILD), "-C", "Release", "--output-on-failure", "-V"],
        LOGS / "stage05_awgn_trial_ctest.log")
    executable = BUILD / "stage05_awgn_trial_runner.exe"
    run([str(executable), str(points_path), str(RESULTS), str(config["masterSeed"])],
        LOGS / "stage05_awgn_trial_runner.log")
    run(["python", str(STAGE / "python" / "stage05_awgn_trial_plot.py")],
        LOGS / "stage05_awgn_trial_plot.log")
    run(["python", str(STAGE / "python" / "stage05_awgn_trial_check.py")],
        LOGS / "stage05_awgn_trial_check.log")


if __name__ == "__main__":
    main()
