#!/usr/bin/env python3
"""Archive Stage14/15 result files before the final-delivery rebuild."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[7]
S3 = SCRIPT.parents[2]
TARGETS = {
    "stage14_block_continuous_comparison":
        "before_hard_slot_completion",
    "stage15_cc_s3_integration":
        "before_final_delivery_rebuild",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO, text=True, encoding="utf-8"
    ).strip()


def archive(stage_name: str, reason: str, head: str) -> None:
    stage = S3 / stage_name
    source = stage / "results"
    archive_root = stage / "archive"
    version = 3
    while (archive_root / f"v{version:02d}_20260731_{reason}").exists():
        version += 1
    target = archive_root / f"v{version:02d}_20260731_{reason}"
    target.mkdir(parents=True)

    for item in sorted(source.iterdir()):
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(target).as_posix(),
                    "sizeBytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "archiveVersion": f"v{version:02d}",
        "archiveDate": "2026-07-31",
        "sourceStage": stage_name,
        "sourceHead": head,
        "reason": reason,
        "copyPolicy": "results only; runtime excluded",
        "files": files,
    }
    (target / "archive_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"ARCHIVED {stage_name} -> {target.relative_to(REPO)}")


def main() -> int:
    if git("branch", "--show-current") != "stage01-cc":
        raise RuntimeError("branch must be stage01-cc")
    status = git("status", "--short")
    expected = f"?? {SCRIPT.relative_to(REPO).as_posix()}"
    if status.strip() != expected:
        raise RuntimeError(f"unexpected worktree state:\n{status}")
    head = git("rev-parse", "HEAD")
    for stage_name, reason in TARGETS.items():
        archive(stage_name, reason, head)
    print("PASS_CC_S3_FINAL_DELIVERY_ARCHIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
