#!/usr/bin/env python3
"""Postprocess completed Stage14 formal data and run the final checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    for script in ("process_final_delivery.py", "check_stage14.py"):
        command = [sys.executable, str(stage / "scripts" / script)]
        print("+", " ".join(command), flush=True)
        subprocess.run(command, cwd=stage, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
