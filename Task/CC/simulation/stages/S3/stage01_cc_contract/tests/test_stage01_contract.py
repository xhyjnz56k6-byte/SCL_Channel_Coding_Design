#!/usr/bin/env python3
"""Independent entry point for the Stage01 positive and negative contract checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    stage_dir = Path(__file__).resolve().parents[1]
    checker = stage_dir / "scripts" / "check_stage01_contract.py"
    completed = subprocess.run(
        [sys.executable, str(checker), "--stage-dir", str(stage_dir)],
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit("Stage01 contract test failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
