import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
STAGE_DIR = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Task" / "BCH" / "simulation" / "build" / "S2" / "stage02_case_contract"
RESULTS = STAGE_DIR / "results"
LOGS = STAGE_DIR / "logs"


def run(command, log=None):
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    print(result.stdout, end="")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(map(str, command))}")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    run(["cmake", "-S", str(STAGE_DIR / "cpp"), "-B", str(BUILD), "-G", "MinGW Makefiles",
         "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", str(BUILD), "--config", "Release", "-j", "2"])
    run(["ctest", "--test-dir", str(BUILD), "-C", "Release", "--output-on-failure", "-V"],
        LOGS / "stage02_case_contract_ctest.log")
    run([str(BUILD / "stage02_case_contract_export.exe"), str(RESULTS)],
        LOGS / "stage02_case_contract_export.log")
    matlab_path = (STAGE_DIR / "matlab").as_posix().replace("'", "''")
    cases = (RESULTS / "stage02_case_contract_cases.csv").as_posix().replace("'", "''")
    output = (RESULTS / "stage02_case_contract_cpp_matlab_compare.csv").as_posix().replace("'", "''")
    command = (
        f"addpath('{matlab_path}'); "
        f"stage02_case_contract_matlab_reference('{cases}','{output}')"
    )
    run(["matlab", "-batch", command], LOGS / "stage02_case_contract_matlab.log")
    run(["python", str(STAGE_DIR / "python" / "stage02_case_contract_check.py")],
        LOGS / "stage02_case_contract_check.log")


if __name__ == "__main__":
    main()
