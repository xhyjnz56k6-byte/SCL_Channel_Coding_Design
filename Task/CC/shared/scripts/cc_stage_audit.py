#!/usr/bin/env python3
"""Reusable Git audit checker for CC stages on a batch branch."""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    stage_dir = manifest_path.parent
    repo = Path(git(stage_dir, "rev-parse", "--show-toplevel").decode().strip())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    branch = git(repo, "branch", "--show-current").decode().strip()
    if branch == "main":
        fail("current branch is main")
    if branch != manifest["branch"]:
        fail(f"branch mismatch: {branch}")
    if manifest["mergeStatus"] != "NOT_MERGED":
        fail("mergeStatus must be NOT_MERGED")

    for functional in manifest["functionalRanges"]:
        base = functional["baseCommit"]
        content = functional["contentCommit"]
        diff_paths = functional.get("diffPaths", [])
        command = ["diff", "--name-only", f"{base}..{content}"]
        if diff_paths:
            command.extend(["--", *diff_paths])
        actual_files = git(repo, *command).decode().splitlines()
        if actual_files != functional["files"]:
            fail(f"functional range {functional['name']} does not match Git diff")

        forbidden_suffixes = (".exe", ".obj", ".o", ".pdb", ".ilk")
        if any(name.lower().endswith(forbidden_suffixes) for name in actual_files):
            fail("compiled artifact in functional range")
        if any("/build/" in name.replace("\\", "/") for name in actual_files):
            fail("build directory in functional range")

    allowed_prefixes = tuple(manifest["scope"]["allowedPrefixes"])
    for functional in manifest["functionalRanges"]:
        for name in functional["files"]:
            if not name.startswith(allowed_prefixes):
                fail(f"out-of-scope file: {name}")

    patch = stage_dir / "changes.patch"
    patch_bytes = patch.read_bytes()
    patch_hash = hashlib.sha256(patch_bytes).hexdigest()
    if patch_hash != manifest["changesPatch"]["sha256"]:
        fail("changes.patch sha256 mismatch")
    if not patch_bytes or b"diff --git " not in patch_bytes:
        fail("changes.patch is empty or invalid")

    report = (stage_dir / "validation_report.md").read_text(encoding="utf-8")
    forbidden_states = ("Pending", "to be run", "NOT_PUSHED", "TO_VERIFY_AFTER_PUSH")
    if any(state in report for state in forbidden_states):
        fail("validation report contains unresolved placeholder state")

    if manifest["gateStatus"] != "PASS":
        fail("gateStatus is not PASS")
    print(f"PASS: {manifest['stage']} functional range matches Git")
    print("PASS: branch, scope, artifact and report checks")
    print(f"PASS: {manifest['gate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
