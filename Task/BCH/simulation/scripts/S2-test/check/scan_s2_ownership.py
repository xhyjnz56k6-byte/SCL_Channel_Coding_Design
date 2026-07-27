"""Inventory S2 BCH assets without changing experiment data."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[6]
SIM = REPO / "Task" / "BCH" / "simulation"
OUT = SIM / "stages" / "S2-test" / "s2_file_ownership.csv"
ROOTS = [
    SIM / "current",
    SIM / "scripts",
    SIM / "stages",
    SIM / "results",
    SIM / "matlab_official_validation",
]
SHARED_NAMES = {
    "bch_awgn_simulation.hpp",
    "bch_awgn_simulation.cpp",
    "bch_awgn_runner.cpp",
    "bch_case_adapter.hpp",
    "bch_case_adapter.cpp",
}


def tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--full-name"],
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def classify(path: Path) -> tuple[str, str, str, str]:
    rel = path.relative_to(REPO).as_posix()
    parts = set(path.parts)
    name = path.name.lower()
    if "results" in parts:
        return "result", "yes", "no", "preserve local result; do not add to Git"
    if any(part.lower().startswith("s2") for part in path.parts):
        return "s2_code_or_audit", "yes", "no", "S2 path or S2 Stage asset"
    if path.name in SHARED_NAMES:
        return "shared_code", "no", "yes", "dependency review required before relocation"
    if "current" in parts and path.suffix.lower() in {".cpp", ".hpp", ".h", ".c", ".cmake", ".txt"}:
        return "shared_or_unclassified_code", "unknown", "unknown", "dependency scan required; do not move yet"
    return "unclassified", "unknown", "unknown", "manual review required"


def main() -> None:
    tracked = tracked_paths()
    rows = []
    for root in ROOTS:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            category, s2_only, shared, reason = classify(path)
            rel = path.relative_to(REPO).as_posix()
            rows.append(
                {
                    "path": rel,
                    "category": category,
                    "s2_only": s2_only,
                    "shared_with_s1": shared,
                    "shared_with_common": "unknown" if shared == "unknown" else ("no" if shared == "no" else "unknown"),
                    "git_tracked": "yes" if rel in tracked else "no",
                    "action": "retain_original" if category == "result" else ("review_then_move" if "unknown" in {s2_only, shared} else "move_to_S2-test"),
                    "reason": reason,
                }
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "category", "s2_only", "shared_with_s1", "shared_with_common", "git_tracked", "action", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
