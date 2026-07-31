#!/usr/bin/env python3
"""Archive the pre-revision Stage09--Stage15 results without overwriting history."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[7]
S3 = SCRIPT.parents[2]
ARCHIVE_DATE = date(2026, 7, 29)
ARCHIVES = {
    "stage09_awgn_formal": "before_two_level_grid_revision",
    "stage10_traceback_study": "before_r34_and_fer_level_extension",
    "stage11_soft_quantization": "before_full_quantization_grid",
    "stage12_continuous_encoder": "before_continuous_encoder_regression",
    "stage13_sliding_window_viterbi": "before_true_window_refactor",
    "stage14_block_continuous_comparison": "before_online_slot_scheduler",
    "stage15_cc_s3_integration": "before_final_integration_rebuild",
}
AUDIT_FILES = (
    "readme.txt",
    "stage_plan.md",
    "manifest.json",
    "validation_report.md",
    "known_issues.md",
    "commands_used.md",
    "frozen_config.csv",
    "result_summary.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO, text=True, encoding="utf-8"
    ).strip()


def next_archive(stage: Path, reason: str) -> tuple[str, Path]:
    archive_root = stage / "archive"
    archive_root.mkdir(exist_ok=True)
    existing = [
        int(path.name[1:3])
        for path in archive_root.iterdir()
        if path.is_dir() and len(path.name) >= 3 and path.name[0] == "v"
        and path.name[1:3].isdigit()
    ]
    version = max(existing, default=0) + 1
    name = f"v{version:02d}_{ARCHIVE_DATE:%Y%m%d}_{reason}"
    target = archive_root / name
    if target.exists():
        raise RuntimeError(f"archive already exists: {target}")
    return f"v{version:02d}", target


def archive_stage(stage_name: str, reason: str, head: str) -> None:
    stage = S3 / stage_name
    results = stage / "results"
    if not results.is_dir():
        raise RuntimeError(f"missing results directory: {results}")
    version, target = next_archive(stage, reason)
    target.mkdir(parents=True)

    for source in sorted(results.iterdir(), key=lambda item: item.name):
        shutil.move(str(source), str(target / source.name))

    audit_snapshot = target / "stage_root_audit_snapshot"
    copied = False
    for name in AUDIT_FILES:
        source = stage / name
        if source.is_file():
            audit_snapshot.mkdir(exist_ok=True)
            shutil.copy2(source, audit_snapshot / name)
            copied = True
    if not copied and audit_snapshot.exists():
        audit_snapshot.rmdir()

    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "archive_manifest.json":
            files.append(
                {
                    "path": path.relative_to(target).as_posix(),
                    "sizeBytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

    manifest = {
        "archiveVersion": version,
        "archiveDate": ARCHIVE_DATE.isoformat(),
        "reason": reason.removeprefix("before_"),
        "sourceStage": stage_name,
        "sourceHead": head,
        "files": files,
        "sha256": hashlib.sha256(
            "\n".join(f"{item['path']}:{item['sha256']}" for item in files).encode()
        ).hexdigest(),
        "previousStatus": "PREVIOUS_REVISION_SNAPSHOT",
        "movePolicy": "results contents moved; stage-root audit files copied as snapshot",
    }
    (target / "archive_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"ARCHIVED {stage_name} -> {target.relative_to(REPO)} ({len(files)} files)")


def main() -> int:
    if Path(git("rev-parse", "--show-toplevel")).resolve() != REPO.resolve():
        raise RuntimeError("repository root mismatch")
    if git("branch", "--show-current") != "stage01-cc":
        raise RuntimeError("branch mismatch")
    if git("status", "--short"):
        expected = SCRIPT.relative_to(REPO).as_posix()
        status = git("status", "--short")
        if status.strip() != f"?? {expected}":
            raise RuntimeError(f"worktree is not clean before archive:\n{status}")
    head = git("rev-parse", "HEAD")
    for stage_name, reason in ARCHIVES.items():
        archive_stage(stage_name, reason, head)
    print("PASS_CC_S3_PRE_REVISION_ARCHIVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
