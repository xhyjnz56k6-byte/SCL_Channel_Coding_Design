#!/usr/bin/env python3
"""Generate immutable stage08 manifest and SHA-256 inventory from Git ranges."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

RANGES = [
    (
        "implementation",
        "7d634814ee50c246a84557d137ceb2c0d7120596",
        "e055724b05f86f42c3ffe3e602f842303426f405",
    ),
    (
        "checkpointAndCheckerRepair",
        "e055724b05f86f42c3ffe3e602f842303426f405",
        "5fb6a373263eb6a50d0ef70a14cad16963a0fb3d",
    ),
    (
        "formalData",
        "5fb6a373263eb6a50d0ef70a14cad16963a0fb3d",
        "77910900d1db3eb64142f409b3b68e4ca9db010f",
    ),
]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    repo = stage.parents[5]
    functional_ranges = []
    all_files: set[str] = set()
    for name, base, content in RANGES:
        files = git(repo, "diff", "--name-only", f"{base}...{content}").splitlines()
        functional_ranges.append(
            {"name": name, "baseCommit": base, "contentCommit": content, "files": files}
        )
        all_files.update(files)
    hashes = {}
    for relative in sorted(all_files):
        path = repo / relative
        if path.is_file():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    (stage / "stage08_multipath_formal_file_hashes.json").write_text(
        json.dumps(hashes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest = {
        "stage": "stage08_multipath_formal",
        "branch": "stage07-08-bch-s2-multipath",
        "functionalRanges": functional_ranges,
        "formalRunGitCommit": "5fb6a373263eb6a50d0ef70a14cad16963a0fb3d",
        "formalConfigHash": "457ea7422976679d98dd9ca6857c00c84e2fbb71e546f759d4ff745aac299a84",
        "formalPointCount": 24,
        "formalFrameCount": 391572,
        "gate": "PASS_STAGE08_MULTIPATH_FORMAL",
        "plotGate": "PASS_STAGE08_PLOT_CHECK",
        "remoteVerification": {
            "branch": "stage07-08-bch-s2-multipath",
            "verifiedContentCommit": "77910900d1db3eb64142f409b3b68e4ca9db010f",
            "containsAllFunctionalRanges": True,
        },
        "mergeStatus": "NOT_MERGED",
    }
    (stage / "stage08_multipath_formal_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PASS_STAGE08_AUDIT_ASSETS_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
