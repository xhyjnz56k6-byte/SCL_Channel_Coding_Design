import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
STAGE = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task/BCH/simulation/build/S2/stage09_cfo_validation"
LOGS = STAGE / "logs"

def run(command, log):
    result = subprocess.run(command, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, end="")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / log).write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.returncode)

run(["cmake", "-S", str(STAGE/"cpp"), "-B", str(BUILD),
     "-G", "MinGW Makefiles", "-DCMAKE_BUILD_TYPE=Release"], "stage09_cfo_validation_cmake.log")
run(["cmake", "--build", str(BUILD), "--config", "Release", "-j", "2"],
    "stage09_cfo_validation_build.log")
run(["ctest", "--test-dir", str(BUILD), "-C", "Release", "--output-on-failure", "-V"],
    "stage09_cfo_validation_ctest.log")
matlab_call = (
    f"stage09_cfo_validation_matlab_reference('{STAGE.as_posix()}')")
run(["matlab", "-batch", f"addpath('{(STAGE/'matlab').as_posix()}');{matlab_call}"],
    "stage09_cfo_validation_matlab.log")
run(["python", str(STAGE/"python/stage09_cfo_validation_checker.py")],
    "stage09_cfo_validation_checker.log")
