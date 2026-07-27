import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


STAGE = "stage01_foundation"
ROOT = Path(__file__).resolve().parents[7]
STAGE_DIR = Path(__file__).resolve().parents[1]
CPP_DIR = STAGE_DIR / "cpp"
BUILD_DIR = ROOT / "Task" / "BCH" / "simulation" / "build" / "S2" / STAGE
RESULTS_DIR = STAGE_DIR / "results"
LOGS_DIR = STAGE_DIR / "logs"


def run(command, log_path=None):
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(result.stdout, encoding="utf-8")
    print(result.stdout, end="")
    if result.returncode:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(map(str, command))}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    generator = "MinGW Makefiles"
    run(["cmake", "-S", str(CPP_DIR), "-B", str(BUILD_DIR), "-G", generator, "-DCMAKE_BUILD_TYPE=Release"])
    run(["cmake", "--build", str(BUILD_DIR), "--config", "Release", "-j", "2"])
    run(
        ["ctest", "--test-dir", str(BUILD_DIR), "-C", "Release", "--output-on-failure", "-V"],
        LOGS_DIR / "stage01_foundation_ctest.log",
    )
    executable = BUILD_DIR / "stage01_foundation_export.exe"
    run([str(executable), str(RESULTS_DIR)], LOGS_DIR / "stage01_foundation_export.log")

    matlab_script = (STAGE_DIR / "matlab").as_posix().replace("'", "''")
    input_csv = (RESULTS_DIR / "stage01_foundation_awgn_vectors.csv").as_posix().replace("'", "''")
    output_csv = (RESULTS_DIR / "stage01_foundation_matlab_outputs.csv").as_posix().replace("'", "''")
    batch = (
        f"addpath('{matlab_script}'); "
        f"stage01_foundation_matlab_reference('{input_csv}','{output_csv}')"
    )
    run(["matlab", "-batch", batch], LOGS_DIR / "stage01_foundation_matlab.log")
    run(
        [
            shutil.which("python") or "python",
            str(STAGE_DIR / "python" / "stage01_foundation_compare.py"),
            "--cpp",
            str(RESULTS_DIR / "stage01_foundation_cpp_outputs.csv"),
            "--matlab",
            str(RESULTS_DIR / "stage01_foundation_matlab_outputs.csv"),
            "--output",
            str(RESULTS_DIR / "stage01_foundation_cpp_matlab_compare.csv"),
        ],
        LOGS_DIR / "stage01_foundation_compare.log",
    )

    files = sorted(
        path for folder in (RESULTS_DIR, LOGS_DIR) for path in folder.iterdir() if path.is_file()
    )
    hashes = [
        {"file": path.relative_to(STAGE_DIR).as_posix(), "sha256": sha256(path), "size": path.stat().st_size}
        for path in files
    ]
    (STAGE_DIR / "stage01_foundation_file_hashes.json").write_text(
        json.dumps(hashes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PASS_STAGE01_FOUNDATION")


if __name__ == "__main__":
    main()
