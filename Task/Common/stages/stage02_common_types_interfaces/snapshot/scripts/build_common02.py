#!/usr/bin/env python
"""Build the Common-02 type/interface skeleton tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str], root: Path) -> None:
    print("RUN:", " ".join(command))
    result = subprocess.run(command, cwd=str(root), text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    source = root / "Task/Common/tests/stage02/test_common02_types_interfaces.cpp"
    output_dir = root / "Task/Common/build/stage02"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "test_common02_types_interfaces.exe"

    command = [
        "g++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(root / "Task/Common/include"),
        str(source),
        "-o",
        str(output),
    ]
    run(command, root)
    print(f"COMMON-02 BUILD: PASS ({output})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

