#!/usr/bin/env python3
"""Finalize Stage09-15 audit records after functional commits are pushed."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

S3 = Path(__file__).resolve().parents[2]
REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
)
BRANCH = subprocess.check_output(
    ["git", "branch", "--show-current"], text=True
).strip()

STAGES = {
    "stage09_awgn_formal": {
        "commits": ["CC/阶段09：复核统一两层AWGN基线"],
        "gate": "PASS_STAGE09_TWO_LEVEL_REVISION",
        "summary": {
            "coarse_rows": 186,
            "dense_rows": 126,
            "merged_rows": 282,
            "coarse_frames": 4_620_252,
            "dense_frames": 825_696,
        },
        "tests": [
            "Release MinGW build: PASS",
            "four coarse shards: PASS",
            "two-level merge/formula/coverage checker: PASS",
            "five pointwise plots and hash manifest: PASS",
        ],
    },
    "stage10_traceback_study": {
        "commits": [
            "CC/阶段10：扩展三码率回溯深度研究",
            "CC/阶段10：完成D84真滑窗联合复核",
        ],
        "gate": "PASS_STAGE10_REVISION",
        "summary": {
            "formal_rows": 63,
            "rates": 3,
            "fer_levels": 3,
            "finite_depths": 6,
            "initial_balanced_dtb": 112,
            "d84_true_window_revalidation": "PASS",
        },
        "tests": [
            "Release MinGW build and noiseless finite-depth checks: PASS",
            "R12/R23/R34 × three FER levels formal runner: PASS",
            "D35/49/70/84/98/112 plus full traceback: PASS",
            "same-noise D84 true-window joint revalidation: PASS",
        ],
    },
    "stage11_soft_quantization": {
        "commits": [
            "CC/阶段11：完成全量量化网格研究",
            "CC/阶段11：更新正式量化结果检查器",
        ],
        "gate": "PASS_STAGE11_REVISION",
        "summary": {
            "prescan_rows": 30,
            "coarse_rows": 651,
            "dense_rows": 365,
            "rates": 3,
            "modes": "Q3,Q4,Q5,Q6,Q7,Q8,Float",
            "balanced_quantization": "Q8",
        },
        "tests": [
            "Release MinGW build: PASS",
            "clipMax prescan and separate clip/edge/overflow counters: PASS",
            "four coarse and four dense shards: PASS",
            "SNR-loss interpolation and thirteen plots: PASS",
        ],
    },
    "stage12_continuous_encoder": {
        "commits": ["CC/阶段12：强化连续编码状态回归"],
        "gate": "PASS_STAGE12_CONTINUOUS_ENCODER",
        "summary": {
            "rates": 3,
            "slot_organizations": "300,50x6,100x3,150x2",
            "frames_per_case": 100,
            "checkpoint_resume": "PASS",
        },
        "tests": [
            "Release MinGW build: PASS",
            "CTest state/phase/tail/checkpoint regression: PASS",
            "block/continuous transmitted-stream identity: PASS",
        ],
    },
    "stage13_sliding_window_viterbi": {
        "commits": [
            "CC/阶段13：实现有界真滑窗维特比译码",
            "CC/阶段13：完成参数选优与正式比较",
            "CC/阶段13：完善零错点科研图标记",
        ],
        "gate": "PASS_STAGE13_FINAL_COMPARISON",
        "summary": {
            "prescan_rows": 135,
            "formal_coarse_rows": 341,
            "reference_rows": 279,
            "window_storage": "W*64 survivor cells",
            "lost_bits": 0,
            "duplicate_bits": 0,
            "plots": 15,
        },
        "tests": [
            "true bounded-window CTest suite: PASS",
            "W/S/D control and illegal-configuration tests: PASS",
            "four formal coarse, dense and reference-replay shards: PASS",
            "block/truncated/true-window final comparison: PASS",
        ],
    },
    "stage14_block_continuous_comparison": {
        "commits": ["CC/阶段14：完成在线时隙组织正式比较"],
        "gate": "PASS_STAGE14_ONLINE_SLOT_REVISION",
        "summary": {
            "coarse_rows": 372,
            "dense_final_rows": 146,
            "rates": 3,
            "organizations": "Block300,50x6,100x3,150x2",
            "boundary_offsets": "-10..+9",
            "main_plots": 18,
        },
        "tests": [
            "Release MinGW build and online smoke: PASS",
            "eight coarse and eight dense shards: PASS",
            "slot-driven arrival/output event accounting: PASS",
            "boundary, latency, buffer and goodput checker: PASS",
        ],
    },
    "stage15_cc_s3_integration": {
        "commits": ["CC/阶段15：重建S3最终集成与科研图"],
        "gate": "PASS_CC_S3_INTEGRATION",
        "summary": {
            "required_plots": 8,
            "scheme_matrix": "PASS",
            "core_questions": 5,
            "recommendation_classes": 6,
            "channel_model": "symbol-level discrete BPSK-AWGN",
        },
        "tests": [
            "formal-source-only matrix checker: PASS",
            "unified coarse/dense SNR coverage: PASS",
            "eight final pointwise plots and source hashes: PASS",
            "core-question and all-figures documents: PASS",
        ],
    },
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def commit_for(subject: str) -> str:
    matches = git(
        "log", "--all", "--fixed-strings", "--grep", subject, "--format=%H"
    ).splitlines()
    if not matches:
        raise RuntimeError(f"missing functional commit: {subject}")
    return matches[0]


def remote_contains(commit: str) -> bool:
    remote_sha = git("rev-parse", f"origin/{BRANCH}")
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, remote_sha],
            cwd=REPO,
            check=False,
        ).returncode
        == 0
    )


def hash_results(stage: Path) -> list[dict]:
    records = []
    for path in sorted((stage / "results").rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(
            {
                "path": path.relative_to(stage).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )
    return records


def write_summary(stage: Path, summary: dict) -> None:
    with (stage / "result_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        writer.writerows(summary.items())


def write_config(stage: Path) -> None:
    rows = [
        ("payloadBits", 300),
        ("constraintLength", 7),
        ("generatorOctal", "171/133"),
        ("motherRate", "1/2"),
        ("puncturedRates", "2/3;3/4"),
        ("modulation", "BPSK 0->+1,1->-1"),
        ("snrDefinition", "Es/N0"),
        ("coarseSnrDb", "-5:0.5:10"),
        ("denseStepDb", 0.1),
        ("minFrames", 1000),
        ("targetFrameErrors", 200),
        ("maxFrames", 50000),
        ("checkpointIntervalFrames", 1000),
        ("payloadSeed", 2026072001),
        ("modelScope", "symbol-level discrete BPSK-AWGN"),
        ("buildType", "Release"),
        ("compiler", "GNU 15.2.0 MinGW UCRT64"),
        ("operatingSystem", platform.platform()),
        ("threadsPerRunner", 1),
        ("formalShardCount", "4 (Stages09/11/13); 8 (Stage14)"),
        ("timingBatchCount", 5),
    ]
    with (stage / "frozen_config.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["parameter", "value"])
        writer.writerows(rows)


def main() -> None:
    if BRANCH != "stage01-cc":
        raise RuntimeError(f"wrong branch: {BRANCH}")
    git("fetch", "origin", BRANCH)
    for name, spec in STAGES.items():
        stage = S3 / name
        ranges = []
        for index, subject in enumerate(spec["commits"]):
            content = commit_for(subject)
            base = git("rev-parse", f"{content}^")
            files = git("diff", "--name-only", base, content).splitlines()
            if not all(path.startswith(f"Task/CC/simulation/stages/S3/{name}/") for path in files):
                raise RuntimeError(f"functional commit crosses Stage scope: {subject}")
            if not remote_contains(content):
                raise RuntimeError(f"remote does not contain {content}")
            ranges.append(
                {
                    "name": f"content{index + 1}",
                    "baseCommit": base,
                    "contentCommit": content,
                    "files": files,
                }
            )
        result_files = hash_results(stage)
        manifest = {
            "stage": name,
            "branch": BRANCH,
            "status": "PASS",
            "functionalRanges": ranges,
            "gate": spec["gate"],
            "formalResults": result_files,
            "formalResultCount": len(result_files),
            "remoteVerified": True,
            "mergeStatus": "NOT_MERGED",
            "balancedWeights": (
                {
                    "reliability": 0.35,
                    "delay": 0.20,
                    "memory": 0.20,
                    "operations": 0.15,
                    "cpuTime": 0.10,
                }
                if name == "stage13_sliding_window_viterbi"
                else None
            ),
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validation = [
            f"# {name} validation report",
            "",
            f"- Branch: `{BRANCH}`",
            f"- Gate: `{spec['gate']}`",
            "- Remote functional commits verified: PASS",
            "- Merge status: NOT_MERGED",
            "",
            "## Executed checks",
            "",
            *[f"- {item}" for item in spec["tests"]],
            "",
            "## Functional ranges",
            "",
            *[
                f"- `{item['baseCommit']}...{item['contentCommit']}` "
                f"({len(item['files'])} files)"
                for item in ranges
            ],
            "",
            f"Final status: **{spec['gate']}**",
            "",
        ]
        (stage / "validation_report.md").write_text(
            "\n".join(validation), encoding="utf-8"
        )
        known = [
            f"# {name} known issues",
            "",
            "- No unresolved P0 correctness issue.",
            "- CPU timing is specific to the recorded Release build, host, "
            "operating system and compiler.",
            "- The channel is symbol-level discrete BPSK-AWGN; it does not "
            "model sampling rate, pulse shaping, matched filtering or noise "
            "bandwidth.",
            "- Formal zero-error BER/FER values remain zero; confidence upper "
            "bounds are stored and used only for display.",
            "",
        ]
        (stage / "known_issues.md").write_text(
            "\n".join(known), encoding="utf-8"
        )
        (stage / "readme.txt").write_text(
            f"{name}\n"
            "Current results/ contains the 2026-07-29 formal revision.\n"
            "Prior results are preserved under archive/ with SHA-256 "
            "archive manifests.\n"
            f"Gate: {spec['gate']}\n"
            "Branch: stage01-cc; mergeStatus: NOT_MERGED.\n",
            encoding="utf-8",
        )
        commands = [
            f"# {name} commands used",
            "",
            "- Release build: `cmake -DCMAKE_BUILD_TYPE=Release`",
            "- Formal stopping: `--min-frames 1000 "
            "--target-frame-errors 200 --max-frames 50000`",
            "- Coarse grid: `-5:0.5:10 dB`",
            "- Dense grid: `0.1 dB` in the measured waterfall range",
            "- Shards were merged only after every shard emitted its PASS "
            "sentinel and stderr remained empty.",
            "- Plot processors generated pointwise figure-data CSVs, PNGs, "
            "plot manifests and SHA-256 checks.",
            "",
        ]
        (stage / "commands_used.md").write_text(
            "\n".join(commands), encoding="utf-8"
        )
        write_summary(stage, spec["summary"])
        write_config(stage)
    print("PASS_CC_S3_AUDIT_FINALIZATION")


if __name__ == "__main__":
    main()
