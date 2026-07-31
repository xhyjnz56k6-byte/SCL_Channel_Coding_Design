#!/usr/bin/env python3
"""Check Stage01 manifest, functional range and generated patch against Git."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    stage_dir = Path(__file__).resolve().parents[1]
    repo = Path(git(stage_dir, "rev-parse", "--show-toplevel").decode().strip())
    manifest = json.loads((stage_dir / "manifest.json").read_text(encoding="utf-8"))

    if git(repo, "branch", "--show-current").decode().strip() == "main":
        fail("current branch is main")
    if manifest["mergeStatus"] != "NOT_MERGED":
        fail("mergeStatus")
    if manifest["gate"] != "PASS_STAGE01_CC_CONTRACT":
        fail("gate")

    functional = manifest["functionalRanges"][0]
    base = functional["baseCommit"]
    content = functional["contentCommit"]
    stage_rel = stage_dir.relative_to(repo).as_posix()
    diff_lines = git(repo, "diff", "--name-only", f"{base}..{content}", "--", stage_rel).decode().splitlines()
    if diff_lines != functional["files"]:
        fail("manifest file list does not match functional Git diff")

    forbidden_fragments = ("/build/", "/results/formal_", ".exe", ".obj", ".pdb")
    if any(fragment in name for name in diff_lines for fragment in forbidden_fragments):
        fail("forbidden generated artifact in functional range")
    if any(name.startswith(("Task/BCH/", "Task/LDPC/", "Task/Common/")) for name in diff_lines):
        fail("out-of-scope functional file")

    patch_bytes = (stage_dir / "changes.patch").read_bytes()
    expected_hash = hashlib.sha256(patch_bytes).hexdigest()
    if expected_hash != manifest["changesPatch"]["sha256"]:
        fail("changes.patch sha256")
    if not patch_bytes or b"diff --git " not in patch_bytes:
        fail("changes.patch is empty or invalid")

    report = (stage_dir / "validation_report.md").read_text(encoding="utf-8")
    forbidden_states = ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH")
    if any(state in report for state in forbidden_states):
        fail("validation report contains forbidden unresolved state")

    print("PASS: manifest functional range matches Git")
    print("PASS: changes.patch hash and semantics")
    print("PASS: scope and forbidden artifact checks")
    print("PASS: validation report state")
    print("PASS_STAGE01_CC_CONTRACT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
