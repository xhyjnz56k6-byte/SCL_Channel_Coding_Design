#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    build = stage / "build"
    results = stage / "results"
    if "--clean" in sys.argv and build.exists():
        shutil.rmtree(build)
    results.mkdir(parents=True, exist_ok=True)
    run([
        "cmake", "-S", str(stage), "-B", str(build), "-G", "MinGW Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
    ], stage)
    run(["cmake", "--build", str(build), "--parallel"], stage)
    run([str(build / "stage10_traceback_study_runner.exe"), str(results)], stage)
    run([sys.executable, str(stage / "scripts" / "check_stage10.py")], stage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
