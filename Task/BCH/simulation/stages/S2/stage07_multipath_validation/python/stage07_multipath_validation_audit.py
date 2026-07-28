#!/usr/bin/env python3
"""Verify stage07 functional range, scope and remote state."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    manifest = json.loads(
        (stage / "stage07_multipath_validation_manifest.json").read_text(encoding="utf-8")
    )
    if git(repo, "branch", "--show-current") != manifest["branch"]:
        raise RuntimeError("BLOCKED_STAGE07_AUDIT_BRANCH")
    item = manifest["functionalRanges"][0]
    actual = git(
        repo, "diff", "--name-only", f"{item['baseCommit']}...{item['contentCommit']}"
    ).splitlines()
    if actual != item["files"]:
        raise RuntimeError("BLOCKED_STAGE07_AUDIT_FUNCTIONAL_RANGE")
    if any(
        not name.startswith("Task/BCH/")
        or "/build/" in name
        or name.lower().endswith((".exe", ".obj", ".pdb"))
        for name in actual
    ):
        raise RuntimeError("BLOCKED_STAGE07_AUDIT_SCOPE")
    if manifest["gate"] != "PASS_STAGE07_MULTIPATH_VALIDATION":
        raise RuntimeError("BLOCKED_STAGE07_AUDIT_GATE")
    if manifest["mergeStatus"] != "NOT_MERGED":
        raise RuntimeError("BLOCKED_STAGE07_AUDIT_MERGE")
    remote = git(
        repo, "ls-remote", "--heads", "origin", f"refs/heads/{manifest['branch']}"
    ).split()[0]
    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", item["contentCommit"], remote], cwd=repo
    )
    report = (stage / "stage07_multipath_validation_validation_report.md").read_text(
        encoding="utf-8"
    )
    for forbidden in ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"):
        if forbidden in report:
            raise RuntimeError(f"BLOCKED_STAGE07_AUDIT_REPORT:{forbidden}")
    print("PASS_STAGE07_MULTIPATH_VALIDATION_AUDIT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
