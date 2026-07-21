#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "Common" / "build" / "stage03"
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = output_dir / "test_common03_frame_pool.exe"
    command = [
        "g++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(root / "Common" / "include"),
        str(root / "Common" / "tests" / "stage03" / "test_common03_frame_pool.cpp"),
        "-o",
        str(executable),
    ]
    print("RUN:", " ".join(command))
    completed = subprocess.run(command, cwd=root.parents[1])
    if completed.returncode != 0:
        print("COMMON-03 BUILD: FAIL")
        return completed.returncode
    print(f"COMMON-03 BUILD: PASS ({executable})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
