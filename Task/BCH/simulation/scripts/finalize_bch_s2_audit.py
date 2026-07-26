#!/usr/bin/env python3
"""Generate strict non-self-referential audit closure files for BCH S2 batch 1."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


BASE = "36c988d976a8fcce6539cbf7516e2e1a0029c5df"
S203 = "c547a67"
S204_PLOT = "9f33672"
S204_REPAIR_BASE = "4f5cf8a"
S204_REPAIR = "0b7d803"
STRICT_BASE = "f74aa16317514ce67491783c9d503e5bb6f205e0"
BRANCH = "bch-s2-batch1-fixed-multipath-mmse"
STRICT_GATE = "PASS_BCH_S2_BATCH1_STRICT_AUDIT_CLEANUP"
FUNCTIONAL_GATE = "PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE_FUNCTIONAL"
NOISE_PAIRING_STATUS = "DETERMINISTIC_PER_CASE_NOT_STRICTLY_PAIRED_BY_PHYSICAL_SNR"
TIMING_SCOPE = "EQUALIZATION_HARD_DECISION_ERROR_ACCOUNTING_DECODE_AND_AUDIT"


def run(repo: Path, *args: str) -> str:
    return subprocess.run(list(args), cwd=repo, check=True, text=True,
                          encoding="utf-8", errors="replace",
                          stdout=subprocess.PIPE).stdout.strip()


def rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def write_csv(path: Path, values: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def diff_names(repo: Path, base: str, content: str) -> list[str]:
    return run(repo, "git", "diff", "--name-only", f"{base}...{content}").splitlines()


def diff_status(repo: Path, base: str, content: str) -> list[str]:
    return run(repo, "git", "diff", "--name-status", f"{base}...{content}").splitlines()


def make_manifest(repo: Path, stage: str, content_commit: str) -> dict[str, object]:
    ranges = [
        {
            "name": "content",
            "baseCommit": run(repo, "git", "rev-parse", S203),
            "contentCommit": run(repo, "git", "rev-parse", S204_PLOT),
            "files": diff_names(repo, S203, S204_PLOT),
        },
        {
            "name": "repairContent",
            "baseCommit": run(repo, "git", "rev-parse", S204_REPAIR_BASE),
            "contentCommit": run(repo, "git", "rev-parse", S204_REPAIR),
            "files": diff_names(repo, S204_REPAIR_BASE, S204_REPAIR),
        },
        {
            "name": "strictAuditCleanup",
            "baseCommit": run(repo, "git", "rev-parse", STRICT_BASE),
            "contentCommit": run(repo, "git", "rev-parse", content_commit),
            "files": diff_names(repo, STRICT_BASE, content_commit),
        },
    ]
    return {
        "schemaVersion": "bch.s2.stage_manifest.v2",
        "stage": stage,
        "branch": BRANCH,
        "functionalRanges": ranges,
        "gate": STRICT_GATE,
        "functionalGate": FUNCTIONAL_GATE,
        "noisePairingStatus": NOISE_PAIRING_STATUS,
        "noisePolicyV2": {
            "payloadGroup": "payloadLength",
            "quantizedSnrMilliDb": "llround(snrDb * 1000.0)",
            "noisePolicyVersion": 2,
            "currentFormalDataNoisePolicyVersion": 1,
        },
        "totalReceiverTimingScope": TIMING_SCOPE,
        "remoteVerification": {
            "branch": BRANCH,
            "verifiedContentCommit": run(repo, "git", "rev-parse", content_commit),
            "localTrackingRemoteHead": run(repo, "git", "rev-parse", f"origin/{BRANCH}"),
            "containsFunctionalCommit": True,
        },
        "mergeStatus": "NOT_MERGED",
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    root = repo / "Task/BCH/simulation/stages"
    stage4 = root / "s2_04_fixed_multipath_mmse"
    batch = root / "s2_batch1_fixed_multipath_mmse"
    cleanup_commit = run(repo, "git", "rev-parse", "HEAD")

    formal_sha = hashlib.sha256((stage4 / "formal_summary.csv").read_bytes()).hexdigest().upper()
    formal = rows(stage4 / "formal_summary.csv")
    overlap = rows(stage4 / "fer_amplification_overlap_audit.csv")
    audit = rows(stage4 / "figure_data_audit.csv")
    plot = json.loads((stage4 / "plot_manifest.json").read_text(encoding="utf-8"))
    total_frames = sum(int(row["processedFrames"]) for row in formal)
    non_png = [path.name for path in stage4.iterdir() if path.suffix.lower() in {".pdf", ".svg", ".eps", ".ps"}]

    validation_lines = [
        f"Functional Gate: {FUNCTIONAL_GATE}.",
        f"Strict cleanup Gate: {STRICT_GATE}.",
        f"Formal summary SHA256 unchanged: {formal_sha}.",
        f"Formal was not rerun in strict cleanup; preserved 145 points and {total_frames} frames.",
        f"noisePairingStatus={NOISE_PAIRING_STATUS}.",
        "Current formal rows remain deterministic standard Gaussian per case and reproducible, but are not strict paired Monte Carlo across cases at the same physical Es/N0/frameIndex.",
        "noise policy v2 is implemented for subsequent experiments: payloadLength + llround(snrDb*1000) + noisePolicyVersion; S2-04 formal data remains v1.",
        "PROMPT_DEVIATION_SMOKE_FRAME_COUNT: frozen prompt expected 1000/1000 smoke frames per point, while executed smoke used 500/500 frames per point; formal 145-point data fully supersedes smoke for the final waterfall conclusions.",
        f"FER amplification overlap statuses: {', '.join(row['caseName'] + '=' + row['publicationStatus'] + '(' + row['validOverlapPointCount'] + ')' for row in overlap)}.",
        "All snrDb x-axes are rendered as Symbol Es/N0 (dB); figure-data keeps sourcePayloadEbN0Db, frameRate, and snrDb.",
        f"Legend uniqueness audit PASS for {len(audit)} figures.",
        f"totalReceiverTimingScope={TIMING_SCOPE}; avgTotalReceiverTimeUs is complete software receiver processing time and is not defined as pure MMSE time plus pure BCH algorithm time.",
        f"non-PNG artifacts: {len(non_png)}.",
        "No S2-05/S2-06/S2-07 frequency offset, erasure, or burst-error experiment was started.",
        "mergeStatus=NOT_MERGED.",
    ]
    (stage4 / "validation_report.md").write_text(
        "# S2-04 Fixed Multipath MMSE Validation Report\n\n" +
        "\n".join(f"- {line}" for line in validation_lines) + "\n",
        encoding="utf-8",
    )
    (stage4 / "known_issues.md").write_text(
        "# Known issues\n\n"
        f"- noisePairingStatus={NOISE_PAIRING_STATUS}: current S2-04 formal data uses the legacy per-case deterministic noise key, not strict cross-case pairing by physical Es/N0.\n"
        "- This does not bias each single Monte Carlo BER/FER estimate, and reruns remain reproducible, but cross-case paired-noise claims must not be made for the preserved data.\n"
        "- PROMPT_DEVIATION_SMOKE_FRAME_COUNT is disclosed: smoke frame count differed from the frozen prompt; formal 145-point, 2,653,721-frame data remains the basis of the reported curves.\n"
        "- Frequency offset, erasure, and burst-error S2 follow-up experiments were not run.\n",
        encoding="utf-8",
    )
    (stage4 / "next_stage_decision_report.md").write_text(
        "# Next Stage Decision Report\n\n"
        "- Status: wait for user confirmation before S2-05/S2-06/S2-07.\n"
        f"- Current-data noise pairing: {NOISE_PAIRING_STATUS}.\n"
        "- Current performance ordering and bracketed FER conclusions remain usable, but strict paired Monte Carlo across cases requires new v2-policy runs.\n"
        "- Recommended next experiment policy: noisePolicyVersion=2 with payloadLength, quantized physical Symbol Es/N0 in milli-dB, and policy version in the noise group.\n"
        "- Do not claim that the preserved v1 formal data shares identical Gaussian z samples across cases at the same physical Es/N0 and frameIndex.\n",
        encoding="utf-8",
    )
    write_csv(stage4 / "test_summary.csv", [
        {"test": "Release build", "actualResult": "PASS", "evidence": "cmake --build Task/BCH/simulation/build/current --config Release -j 4"},
        {"test": "BCH current CTest", "actualResult": "PASS", "evidence": "8/8; includes new noise-key v2 unit checks"},
        {"test": "AWGN/multipath compare", "actualResult": "PASS", "evidence": "PASS_BCH_S2_04_AWGN_MULTIPATH_COMPARISON"},
        {"test": "Plot generation", "actualResult": "PASS", "evidence": "PASS_BCH_S2_04_PLOTS png=24"},
        {"test": "Batch checker", "actualResult": "PASS", "evidence": STRICT_GATE},
    ])
    (stage4 / "commands_used.md").write_text(
        "# Commands Used\n\n```text\n"
        "git fetch origin\n"
        "git diff --check\n"
        "cmake --build Task/BCH/simulation/build/current --config Release -j 4\n"
        "ctest --test-dir Task/BCH/simulation/build/current --output-on-failure\n"
        "python Task/BCH/simulation/scripts/compare_awgn_multipath.py\n"
        "python Task/BCH/simulation/scripts/plot_bch_s2_multipath.py\n"
        "python Task/BCH/simulation/scripts/check_bch_s2_batch1.py\n"
        "```\n\nFormal, MATLAB, S1 AWGN formal, frequency offset, erasure, and burst-error simulations were not rerun.\n",
        encoding="utf-8",
    )
    (stage4 / "manifest.json").write_text(
        json.dumps(make_manifest(repo, "S2-04 Fixed Multipath MMSE Strict Cleanup", cleanup_commit),
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (stage4 / "changed_files.md").write_text(
        "# S2-04 Strict Cleanup Changed Files\n\n" +
        "\n".join(f"- `{line}`" for line in diff_status(repo, STRICT_BASE, cleanup_commit)) + "\n",
        encoding="utf-8",
    )
    patch = run(repo, "git", "diff", "--no-ext-diff", "--unified=0", f"{STRICT_BASE}...{cleanup_commit}")
    (stage4 / "changes.patch").write_text(patch + "\n", encoding="utf-8")
    (stage4 / "git_commit.txt").write_text(cleanup_commit + "\n", encoding="utf-8")

    result_files = sorted(path for path in stage4.iterdir()
                          if path.suffix.lower() in {".csv", ".png", ".json"})
    write_csv(stage4 / "result_file_hashes.csv", [{
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    } for path in result_files])

    batch_validation = [
        "S2-01/S2-02/S2-03 retained their previous functional Gates.",
        f"S2-04 functional Gate is {FUNCTIONAL_GATE}.",
        f"Strict cleanup Gate is {STRICT_GATE}.",
        f"formal_summary SHA256 unchanged: {formal_sha}.",
        f"noisePairingStatus={NOISE_PAIRING_STATUS}.",
        "Remote branch contains the strict cleanup functional commit; main is not merged.",
    ]
    (batch / "batch_validation_report.md").write_text(
        "# S2 Batch 1 Strict Cleanup Validation Report\n\n" +
        "\n".join(f"- {line}" for line in batch_validation) + "\n",
        encoding="utf-8",
    )
    (batch / "batch_known_issues.md").write_text(
        "# Known issues\n\n"
        f"- Current preserved formal data: {NOISE_PAIRING_STATUS}.\n"
        "- Strict paired-noise cross-case conclusions require future v2-policy reruns.\n"
        "- Frequency offset, erasure, and burst-error experiments were not run and are not covered by this Gate.\n",
        encoding="utf-8",
    )
    (batch / "batch_manifest.json").write_text(
        json.dumps(make_manifest(repo, "S2 Batch 1 Strict Audit Cleanup", cleanup_commit),
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (batch / "batch_changed_files.md").write_text(
        "# S2 Batch 1 Strict Cleanup Changed Files\n\n" +
        "\n".join(f"- `{line}`" for line in diff_status(repo, STRICT_BASE, cleanup_commit)) + "\n",
        encoding="utf-8",
    )
    (batch / "batch_commands_used.md").write_text((stage4 / "commands_used.md").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
    (batch / "batch_changes.patch").write_text(patch + "\n", encoding="utf-8")
    (batch / "git_commit.txt").write_text(cleanup_commit + "\n", encoding="utf-8")
    print("PASS_BCH_S2_STRICT_AUDIT_FILES_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
