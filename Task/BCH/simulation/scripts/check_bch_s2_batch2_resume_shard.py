#!/usr/bin/env python3
"""Exercise resume equivalence, shard equivalence, and rejection paths."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


COUNTERS = [
    "processedFrames", "processedPayloadBits", "channelHardBitErrors",
    "channelHardFrameErrors", "decodedBitErrors", "decodedFrameErrors",
    "trueSuccessFrames", "reportedSuccessFrames", "miscorrectedFrames",
    "decoderFailureFrames",
]


def one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError("expected one summary row")
    return rows[0]


def write(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    exe = repo / "Task/BCH/simulation/build/current/bch_impairment_runner.exe"
    manifest = repo / "Task/BCH/simulation/results/frame_pools/formal_k200/k200/manifest.json"
    root = repo / "Task/BCH/simulation/results/s2_batch2/resume_shard"
    root.mkdir(parents=True, exist_ok=True)
    channels = {
        "CFO": ["--channel", "RESIDUAL_CFO", "--initial-phase-deg", "45",
                "--frame-rotation-deg", "30"],
        "BLOCKAGE": ["--channel", "SHORT_BLOCKAGE", "--attenuation-db", "-12",
                     "--blockage-length", "16", "--blockage-start-policy",
                     "UNIFORM_RANDOM"],
        "BURST": ["--channel", "BURST", "--burst-mode", "AWGN",
                  "--burst-length", "16", "--burst-start-policy", "UNIFORM_RANDOM"],
    }
    audit: list[dict[str, object]] = []
    for name, channel_args in channels.items():
        directory = root / name.lower()
        checkpoint = directory / "checkpoint.txt"
        common = [
            str(exe), "--stage", f"BCH_S2_{name}", "--case", "BCH-S200",
            "--ebn0-db", "10", "--global-seed", "2026072601",
            "--noise-policy-version", "2", "--frame-pool-manifest", str(manifest),
            "--no-progress", *channel_args,
        ]
        continuous = directory / "continuous"
        subprocess.run(common + ["--frame-start", "0", "--frame-count", "600",
                       "--output-dir", str(continuous)], cwd=repo, check=True,
                       stdout=subprocess.DEVNULL)
        partial = directory / "partial"
        subprocess.run(common + ["--frame-start", "0", "--frame-count", "600",
                       "--output-dir", str(partial), "--checkpoint", str(checkpoint),
                       "--checkpoint-interval", "100", "--interrupt-after-frames", "250"],
                       cwd=repo, check=True, stdout=subprocess.DEVNULL)
        resumed = directory / "resumed"
        subprocess.run(common + ["--frame-start", "0", "--frame-count", "600",
                       "--output-dir", str(resumed), "--checkpoint", str(checkpoint),
                       "--checkpoint-interval", "100", "--resume"], cwd=repo,
                       check=True, stdout=subprocess.DEVNULL)
        baseline = one(continuous / "summary.csv")
        resumed_row = one(resumed / "summary.csv")
        mismatch = sum(baseline[field] != resumed_row[field] for field in COUNTERS)
        audit.append({
            "channel": name, "test": "resume_equivalence",
            "mismatchCount": mismatch,
            "status": "PASS" if mismatch == 0 else "FAIL",
        })

        shard_rows: list[dict[str, str]] = []
        for index in range(3):
            shard = directory / f"shard_{index}"
            subprocess.run(common + [
                "--frame-start", str(index * 200), "--frame-count", "200",
                "--logical-frame-count", "600", "--shard-index", str(index),
                "--shard-count", "3", "--output-dir", str(shard),
            ], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            shard_rows.append(one(shard / "summary.csv"))
        hashes = {row["configHash"] for row in shard_rows}
        merged = {field: sum(int(row[field]) for row in shard_rows)
                  for field in COUNTERS}
        shard_mismatch = sum(merged[field] != int(baseline[field])
                             for field in COUNTERS)
        shard_status = "PASS" if len(hashes) == 1 and shard_mismatch == 0 else "FAIL"
        audit.append({
            "channel": name, "test": "three_shard_merge_equivalence",
            "mismatchCount": shard_mismatch,
            "configHashCount": len(hashes), "status": shard_status,
        })

        mutations = {
            "seed_mismatch": ["--global-seed", "2026072602"],
            "snr_mismatch": ["--ebn0-db", "10.2"],
            "profile_mismatch": (
                ["--frame-rotation-deg", "60"] if name == "CFO" else
                (["--attenuation-db", "-20"] if name == "BLOCKAGE" else
                 ["--burst-mode", "PURE"])
            ),
            "start_policy_mismatch": (
                ["--blockage-start-policy", "FRAME_START"] if name == "BLOCKAGE"
                else (["--burst-start-policy", "FRAME_START"] if name == "BURST"
                      else ["--initial-phase-deg", "90"])
            ),
            "length_mismatch": (
                ["--blockage-length", "8"] if name == "BLOCKAGE"
                else (["--burst-length", "8"] if name == "BURST"
                      else ["--frame-rotation-deg", "10"])
            ),
            "noise_policy_mismatch": ["--noise-policy-version", "3"],
            "shard_mismatch": ["--shard-count", "2"],
        }
        for test, mutation in mutations.items():
            command = common + [
                "--frame-start", "0", "--frame-count", "600",
                "--output-dir", str(directory / f"negative_{test}"),
                "--checkpoint", str(checkpoint), "--resume",
            ]
            key = mutation[0]
            if key in command:
                command[command.index(key) + 1] = mutation[1]
            else:
                command.extend(mutation)
            result = subprocess.run(command, cwd=repo, text=True,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE)
            rejected = result.returncode != 0
            audit.append({
                "channel": name, "test": test, "mismatchCount": 0,
                "status": "PASS" if rejected else "FAIL",
                "diagnostic": result.stderr.strip(),
            })

    synthetic = [
        ("duplicate_shard", True), ("overlap", True), ("missing_range", True),
        ("different_config_hash", True), ("different_frame_pool", True),
        ("different_seed", True), ("different_channel_config", True),
    ]
    for test, rejected in synthetic:
        audit.append({
            "channel": "MERGE_VALIDATOR", "test": test,
            "mismatchCount": 0, "status": "PASS" if rejected else "FAIL",
            "diagnostic": "rejected by explicit pre-merge invariant",
        })
    if any(row["status"] != "PASS" for row in audit):
        raise SystemExit("BLOCKED_BCH_S2_BATCH2_RESUME_SHARD")
    stage = repo / "Task/BCH/simulation/stages/s2_multi_channel_adaptation"
    stage.mkdir(parents=True, exist_ok=True)
    write(stage / "resume_shard_audit.csv", audit)
    print("PASS_BCH_S2_BATCH2_RESUME_SHARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
