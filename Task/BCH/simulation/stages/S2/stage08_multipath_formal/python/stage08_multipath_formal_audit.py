#!/usr/bin/env python3
"""Strict Git and artifact audit for stage08."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    manifest = json.loads(
        (stage / "stage08_multipath_formal_manifest.json").read_text(encoding="utf-8")
    )
    if git(repo, "branch", "--show-current") != manifest["branch"]:
        raise RuntimeError("BLOCKED_STAGE08_AUDIT_BRANCH")
    for item in manifest["functionalRanges"]:
        actual = git(
            repo, "diff", "--name-only",
            f"{item['baseCommit']}...{item['contentCommit']}",
        ).splitlines()
        if actual != item["files"]:
            raise RuntimeError(f"BLOCKED_STAGE08_AUDIT_RANGE:{item['name']}")
        if any(
            not name.startswith("Task/BCH/")
            or "/build/" in name
            or "/checkpoints/" in name
            or "/initial_e055724/" in name
            or name.lower().endswith((".exe", ".obj", ".pdb", ".pdf", ".svg", ".eps", ".jpg", ".jpeg"))
            for name in actual
        ):
            raise RuntimeError(f"BLOCKED_STAGE08_AUDIT_SCOPE:{item['name']}")
    if manifest["gate"] != "PASS_STAGE08_MULTIPATH_FORMAL":
        raise RuntimeError("BLOCKED_STAGE08_AUDIT_GATE")
    if manifest["plotGate"] != "PASS_STAGE08_PLOT_CHECK":
        raise RuntimeError("BLOCKED_STAGE08_AUDIT_PLOT")
    if manifest["mergeStatus"] != "NOT_MERGED":
        raise RuntimeError("BLOCKED_STAGE08_AUDIT_MERGE")
    remote_line = git(
        repo, "ls-remote", "--heads", "origin", f"refs/heads/{manifest['branch']}"
    )
    remote = remote_line.split()[0]
    for item in manifest["functionalRanges"]:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", item["contentCommit"], remote],
            cwd=repo,
        )
    report = (stage / "stage08_multipath_formal_validation_report.md").read_text(
        encoding="utf-8"
    )
    for forbidden in ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH"):
        if forbidden in report:
            raise RuntimeError(f"BLOCKED_STAGE08_AUDIT_REPORT:{forbidden}")
    subprocess.check_call(
        ["python", str(stage / "python/stage08_multipath_formal_check.py")], cwd=repo
    )
    subprocess.check_call(
        ["python", str(stage / "python/stage08_multipath_formal_plot_check.py")], cwd=repo
    )
    print("PASS_STAGE08_MULTIPATH_FORMAL_AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
