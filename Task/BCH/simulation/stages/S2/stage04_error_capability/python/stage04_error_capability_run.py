import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task" / "BCH" / "simulation" / "build" / "S2" / "stage04_error_capability"
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


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    run(["cmake", "-S", str(STAGE / "cpp"), "-B", str(BUILD), "-G", "MinGW Makefiles",
         "-DCMAKE_BUILD_TYPE=Release", f"-DSTAGE04_OUTPUT_DIR={RESULTS.as_posix()}"])
    run(["cmake", "--build", str(BUILD), "--config", "Release", "-j", "2"])
    run(["ctest", "--test-dir", str(BUILD), "-C", "Release", "--output-on-failure", "-V"],
        LOGS / "stage04_error_capability_ctest.log")
    matlab_path = (STAGE / "matlab").as_posix().replace("'", "''")
    segmented = (ROOT / "Task" / "BCH" / "segmented" / "matlab").as_posix().replace("'", "''")
    samples = (RESULTS / "stage04_error_capability_cpp_matlab_samples.csv").as_posix().replace("'", "''")
    compare = (RESULTS / "stage04_error_capability_cpp_matlab_compare.csv").as_posix().replace("'", "''")
    batch = (
        f"addpath('{matlab_path}'); "
        f"stage04_error_capability_matlab_reference('{samples}','{compare}','{segmented}')"
    )
    run(["matlab", "-batch", batch], LOGS / "stage04_error_capability_matlab.log")
    run(["python", str(STAGE / "python" / "stage04_error_capability_check.py")],
        LOGS / "stage04_error_capability_check.log")


if __name__ == "__main__":
    main()
