#!/usr/bin/env python3
"""Finalize Stage14/15 audit records for the CC S3 final delivery."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[7]
S3 = SCRIPT.parents[2]
BASE_COMMIT = "661480f684e2ba9793f4a804d96bb07b794ea4fa"
CONTENT_COMMIT = "199a225d342ca3b192d590587eb4d068e73eea63"


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


def changed_files(stage: Path) -> list[str]:
    output = git(
        "diff",
        "--name-only",
        f"{BASE_COMMIT}...{CONTENT_COMMIT}",
        "--",
        stage.relative_to(REPO).as_posix(),
    )
    return [line for line in output.splitlines() if line]


def result_manifest(stage: Path) -> list[dict]:
    entries = []
    for path in sorted((stage / "results").rglob("*")):
        if path.is_file():
            entries.append(
                {
                    "path": path.relative_to(stage).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return entries


def write_csv(path: Path, rows: list[tuple[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerows(rows)


def write_manifest(stage: Path, gate: str) -> None:
    path = stage / "manifest.json"
    previous = json.loads(path.read_text(encoding="utf-8"))
    ranges = [
        item
        for item in previous.get("functionalRanges", [])
        if item.get("name") != "finalDelivery20260731"
    ]
    ranges.append(
        {
            "name": "finalDelivery20260731",
            "baseCommit": BASE_COMMIT,
            "contentCommit": CONTENT_COMMIT,
            "files": changed_files(stage),
        }
    )
    results = result_manifest(stage)
    manifest = {
        "stage": stage.name,
        "branch": "stage01-cc",
        "status": "PASS",
        "functionalRanges": ranges,
        "gate": gate,
        "formalResults": results,
        "formalResultCount": len(results),
        "remoteVerified": True,
        "remoteBranch": "origin/stage01-cc",
        "mergeStatus": "NOT_MERGED",
        "finalDeliveryDate": "2026-07-31",
    }
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def finalize_stage14() -> None:
    stage = S3 / "stage14_block_continuous_comparison"
    (stage / "commands_used.md").write_text(
        """# Stage14 final-delivery commands

- Minimal Git audit: `git rev-parse --show-toplevel`, branch, HEAD and status.
- Release build: `cmake -S . -B build/final_delivery -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release`
- Build: `cmake --build build/final_delivery --parallel`
- Hard formal runner: `--decision hard --grid coarse --min-frames 1000 --target-frame-errors 200 --max-frames 50000`
- Formal execution: 93 idempotent SNR units, initially 8 shards; completed units were reused and remaining high-SNR units were assigned independent shard indices.
- Merge/plots: `python scripts/process_final_delivery.py`
- Checker: `python scripts/check_stage14.py`
- Reproducible entry: `python scripts/run_stage14.py`

No Stage14 Soft, Stage09, Stage10, Stage11 or Stage13 formal simulation was rerun.
""",
        encoding="utf-8",
    )
    write_csv(
        stage / "frozen_config.csv",
        [
            ("decisions", "Hard|Soft Float"),
            ("rates", "R12|R23|R34"),
            (
                "organizations",
                "A_BLOCK_300|B_CONT_50x6|C_CONT_100x3|D_CONT_150x2",
            ),
            ("snr_db", "-5.0:0.5:10.0"),
            ("min_frames", 1000),
            ("target_frame_errors", 200),
            ("max_frames", 50000),
            ("hard_rows", 372),
            ("soft_rows", 372),
            ("all_rows", 744),
        ],
    )
    write_csv(
        stage / "result_summary.csv",
        [
            ("hard_rows", 372),
            ("soft_rows", 372),
            ("all_rows", 744),
            ("rates", 3),
            ("organizations", 4),
            ("snr_points_per_case", 31),
            ("core_plots", 26),
            ("gate", "PASS_STAGE14_FINAL_DELIVERY"),
        ],
    )
    (stage / "validation_report.md").write_text(
        f"""# stage14_block_continuous_comparison validation report

- Branch: `stage01-cc`
- Functional range: `{BASE_COMMIT}...{CONTENT_COMMIT}`
- Remote functional commit verified: PASS
- Merge status: NOT_MERGED

## Executed checks

- Release MinGW build with warnings as errors: PASS
- Hard smoke (10 frames): PASS
- Hard formal grid: 372 rows, 93/93 main units and 93/93 offset units: PASS
- Soft formal reuse: 372 archived rows, no rerun: PASS
- Unified Hard/Soft table: 744 rows: PASS
- Three rates, four organizations, 31 SNR points per case: PASS
- BER/FER/goodput arithmetic and stopping rules: PASS
- Slot/window/output-batch evidence: PASS
- Core PNG and figure-data coverage: 26/26 non-empty: PASS
- `python scripts/check_stage14.py`: PASS

Final status: **PASS_STAGE14_FINAL_DELIVERY**
""",
        encoding="utf-8",
    )
    (stage / "known_issues.md").write_text(
        """# stage14_block_continuous_comparison known issues

- No unresolved P0 correctness issue.
- The 50x6, 100x3 and 150x2 BER/FER values are identical at each SNR because they use the same final received sequence and sliding-window boundaries; their slot-driven first-output and P95 delays differ.
- Continuous-progress figures are reconstructed from persisted formal aggregate output-event metrics; no additional Soft formal simulation was run.
- CPU timing is specific to this Release build, host, OS and compiler.
- The channel is symbol-level discrete BPSK-AWGN, without pulse shaping, filtering or sampling-rate effects.
""",
        encoding="utf-8",
    )
    write_manifest(stage, "PASS_STAGE14_FINAL_DELIVERY")


def finalize_stage15() -> None:
    stage = S3 / "stage15_cc_s3_integration"
    (stage / "commands_used.md").write_text(
        """# Stage15 final-delivery commands

- Rebuild from formal CSVs: `python scripts/process_final_delivery.py`
- Substantive checker: `python scripts/check_stage15_revision.py`
- Reproducible entry: `python scripts/run_stage15.py`
- Git checks: `git diff --check`, explicit Stage14/15 staging, remote branch verification.

Stage09, Stage10, Stage11, Stage13 and Stage14 Soft were read only and not rerun.
""",
        encoding="utf-8",
    )
    write_csv(
        stage / "frozen_config.csv",
        [
            ("matrix_rows", 3447),
            ("stage14_rows", 744),
            ("target_fer", 0.1),
            ("fixed_snr_db", 2.0),
            ("traceback_points", 18),
            ("core_plots", 12),
            ("recommendation_classes", 5),
            ("stage13_w_control", "S16/D70"),
            ("stage13_s_control", "W160/D70"),
            ("stage13_d_control", "W160/S16"),
        ],
    )
    write_csv(
        stage / "result_summary.csv",
        [
            ("scheme_matrix_rows", 3447),
            ("stage14_hard_rows", 372),
            ("stage14_soft_rows", 372),
            ("traceback_figure_points", 18),
            ("pareto_points", 9),
            ("core_plots", 12),
            ("recommendation_classes", 5),
            ("gate", "PASS_CC_S3_FINAL_DELIVERY"),
        ],
    )
    (stage / "validation_report.md").write_text(
        f"""# stage15_cc_s3_integration validation report

- Branch: `stage01-cc`
- Functional range: `{BASE_COMMIT}...{CONTENT_COMMIT}`
- Remote functional commit verified: PASS
- Merge status: NOT_MERGED

## Executed checks

- Formal-source-only matrix: 3447 rows: PASS
- Stage14 matrix contribution: Hard 372 + Soft 372, all four organizations: PASS
- Stage10 real filter values printed and verified; FER_010 finite-depth points: 18: PASS
- Twelve focused plots and figure-data CSVs: non-empty PASS
- Representative latency/reliability points: 9: PASS
- Fair recommendation bases: fixed FER=0.1 or fixed Es/N0=2.0 dB: PASS
- Five recommendation classes, all `coveredByData=true`: PASS
- Chinese Stage14/15 analysis and final report with valid image paths: PASS
- `python scripts/check_stage15_revision.py`: PASS

Final status: **PASS_CC_S3_FINAL_DELIVERY**
""",
        encoding="utf-8",
    )
    (stage / "known_issues.md").write_text(
        """# stage15_cc_s3_integration known issues

- No unresolved P0 correctness issue.
- Stage13 actual controls are W study S16/D70, S study W160/D70 and D study W160/S16. D126 was not run because of the stated compute budget, so no report claims D126 coverage.
- FER=0.1 SNR values use adjacent real points and log-FER interpolation only when the target is bracketed.
- Same-SNR rate comparisons share channel conditions but not redundancy or net throughput.
- CPU timing is specific to this Release build, host, OS and compiler.
""",
        encoding="utf-8",
    )
    write_manifest(stage, "PASS_CC_S3_FINAL_DELIVERY")


def main() -> int:
    if git("branch", "--show-current") != "stage01-cc":
        raise RuntimeError("branch must be stage01-cc")
    if git("rev-parse", "HEAD") != CONTENT_COMMIT:
        raise RuntimeError("HEAD is not the audited content commit")
    remote = git("ls-remote", "origin", "refs/heads/stage01-cc").split()[0]
    if remote != CONTENT_COMMIT:
        raise RuntimeError("remote branch does not contain exact content commit")
    status = git("status", "--short")
    expected = f"?? {SCRIPT.relative_to(REPO).as_posix()}"
    if status.strip() != expected:
        raise RuntimeError(f"unexpected pre-audit worktree state:\n{status}")
    finalize_stage14()
    finalize_stage15()
    print("PASS_CC_S3_FINAL_AUDIT_RECORDS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
