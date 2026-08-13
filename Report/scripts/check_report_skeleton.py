#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2] / "报告"
required = [root / "main.tex", root / "README.md", root / "evidence" / "source_inventory.csv", root / "evidence" / "scan_manifest.json"]
missing = [str(x) for x in required if not x.exists() or x.stat().st_size == 0]
text = (root / "main.tex").read_text(encoding="utf-8") if (root / "main.tex").exists() else ""
forbidden = [x for x in ("\\begin{abstract}", "\\chapter{绪论}") if x in text]
if missing or forbidden:
    print("FAIL", "missing=", missing, "forbidden=", forbidden); sys.exit(1)
print("PASS: report skeleton and core inventories are present.")
