#!/usr/bin/env python3
"""Package current Stage09-15 result/audit files for local upload."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

S3 = Path(__file__).resolve().parents[2]
OUTPUT = S3 / "cc_s3_upload_20260729.zip"
MANIFEST = S3 / "cc_s3_upload_20260729_manifest.json"
STAGE_NAMES = [
    "stage09_awgn_formal",
    "stage10_traceback_study",
    "stage11_soft_quantization",
    "stage12_continuous_encoder",
    "stage13_sliding_window_viterbi",
    "stage14_block_continuous_comparison",
    "stage15_cc_s3_integration",
]
AUDIT_NAMES = [
    "stage_plan.md",
    "manifest.json",
    "validation_report.md",
    "known_issues.md",
    "commands_used.md",
    "frozen_config.csv",
    "result_summary.csv",
    "readme.txt",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    files: list[Path] = []
    for name in STAGE_NAMES:
        stage = S3 / name
        files.extend(path for path in (stage / "results").rglob("*") if path.is_file())
        files.extend(
            stage / audit_name
            for audit_name in AUDIT_NAMES
            if (stage / audit_name).is_file()
        )
    records = []
    with zipfile.ZipFile(
        OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path in sorted(set(files)):
            relative = path.relative_to(S3).as_posix()
            archive.write(path, relative)
            records.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "archive": OUTPUT.name,
        "archiveBytes": OUTPUT.stat().st_size,
        "archiveSha256": sha256(OUTPUT),
        "fileCount": len(records),
        "files": records,
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"PASS_CC_S3_UPLOAD_PACKAGE files={len(records)} "
        f"sha256={manifest['archiveSha256']}"
    )


if __name__ == "__main__":
    main()
