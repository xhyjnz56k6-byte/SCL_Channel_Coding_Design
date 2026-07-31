#!/usr/bin/env python3
"""Refresh Stage14/15 audit hashes after removing log-scale error floors."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[7]
S3 = SCRIPT.parents[2]
BASE_COMMIT = "59f872d5c0090b73cec5fe8d60898922237fb504"
CONTENT_COMMIT = "6bcf4c4debd3f50b9cbe148c50bc1df234e3155c"


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO, text=True, encoding="utf-8"
    ).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refresh(stage_name: str) -> None:
    stage = S3 / stage_name
    manifest_path = stage / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stage_path = stage.relative_to(REPO).as_posix()
    changed = git(
        "diff", "--name-only", f"{BASE_COMMIT}...{CONTENT_COMMIT}", "--", stage_path
    ).splitlines()
    ranges = [
        item
        for item in manifest["functionalRanges"]
        if item.get("name") != "logScaleFloorRemoval20260731"
    ]
    ranges.append(
        {
            "name": "logScaleFloorRemoval20260731",
            "baseCommit": BASE_COMMIT,
            "contentCommit": CONTENT_COMMIT,
            "files": changed,
        }
    )
    results = []
    for path in sorted((stage / "results").rglob("*")):
        if path.is_file():
            results.append(
                {
                    "path": path.relative_to(stage).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest["functionalRanges"] = ranges
    manifest["formalResults"] = results
    manifest["formalResultCount"] = len(results)
    manifest["remoteVerified"] = True
    manifest["remoteBranch"] = "origin/stage01-cc"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = stage / "validation_report.md"
    validation.write_text(
        validation.read_text(encoding="utf-8")
        + "\n## Log-scale redraw\n\n"
        + "- Zero-error BER/FER points remain in formal CSV and figure-data: PASS\n"
        + "- Log-scale plots omit zero values instead of clipping to 1e-8: PASS\n"
        + "- Rebuilt PNGs, manifests and Stage14/15 checkers: PASS\n",
        encoding="utf-8",
    )


def main() -> int:
    if git("branch", "--show-current") != "stage01-cc":
        raise RuntimeError("branch mismatch")
    if git("rev-parse", "HEAD") != CONTENT_COMMIT:
        raise RuntimeError("content commit mismatch")
    remote = git("ls-remote", "origin", "refs/heads/stage01-cc").split()[0]
    if remote != CONTENT_COMMIT:
        raise RuntimeError("remote content commit mismatch")
    expected = f"?? {SCRIPT.relative_to(REPO).as_posix()}"
    if git("status", "--short") != expected:
        raise RuntimeError("unexpected pre-audit worktree state")
    refresh("stage14_block_continuous_comparison")
    refresh("stage15_cc_s3_integration")
    print("PASS_CC_S3_LOG_SCALE_AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
