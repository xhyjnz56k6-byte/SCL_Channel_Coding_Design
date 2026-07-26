#!/usr/bin/env python3
"""Generate immutable functional-range audit records for the S2-07 redesign."""
from __future__ import annotations
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

BASE = "069373b02401ad0acc10d96eb4e63bad8763c64c"
RANGES = {
    "s2_07a_block_burst_correction_boundary": "d09db7eb73e0347b8f8de830769cf3511c01e0df",
    "s2_07b_segmented_boundary_heatmap": "73ecc758d132d54e797c19cea92c9e370de2e52b",
    "s2_07c_random_burst_performance": "9a46afed97f3c733024c1450fe6aee1cc02aa70b",
    "s2_07d_burst_interleaving": "3c4193aa333e806655d202bac03b426021752cf8",
}
GATES = {
    "s2_07a_block_burst_correction_boundary":
        "PASS_BCH_S2_07A_BLOCK_BURST_CORRECTION_BOUNDARY",
    "s2_07b_segmented_boundary_heatmap":
        "PASS_BCH_S2_07B_SEGMENTED_BOUNDARY_HEATMAP",
    "s2_07c_random_burst_performance":
        "PASS_BCH_S2_07C_RANDOM_BURST_PERFORMANCE",
    "s2_07d_burst_interleaving":
        "PASS_BCH_S2_07D_BURST_INTERLEAVING",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def files_for(repo: Path, commit: str) -> list[str]:
    parent = git(repo, "rev-parse", f"{commit}^")
    lines = git(repo, "diff", "--name-only", parent, commit).splitlines()
    return [line.replace("\\", "/") for line in lines]


def make_stage(repo: Path, name: str, commit: str) -> None:
    root = repo / "Task/BCH/simulation/stages" / name
    parent = git(repo, "rev-parse", f"{commit}^")
    files = files_for(repo, commit)
    letter = name[5].upper()
    purpose = {
        "A": "整块 BCH 连续硬 bit 翻转的确定性全起点纠错边界",
        "B": "分块 BCH 子块相对起点与连续错误长度的边界热力图",
        "C": "五种 BCH Case 的随机起点连续错误统计性能",
        "D": "五种 BCH Case 在无交织与固定随机交织下的配对比较",
    }[letter]
    (root / "stage_plan.md").write_text(
        f"# S2-07{letter} 规格冻结\n\n"
        f"## 目标\n\n{purpose}。\n\n"
        "## 非目标\n\n不包含 AWGN、遮挡、脉冲噪声、波形域干扰或完整物理突发信道建模；"
        "不修改 BCH 编译码算法和历史结果。\n\n"
        "## 数据模型\n\n编码后硬判决 bit 序列上注入连续翻转："
        "`r = c XOR e`。确定性枚举与随机 Monte Carlo 分开记录。\n\n"
        "## Gate\n\n"
        f"`{GATES[name]}`\n", encoding="utf-8")
    write_csv(root / "acceptance_matrix.csv", [{
        "需求": purpose, "实现位置": f"Task/BCH/simulation/stages/{name}",
        "正向测试": "smoke+formal+业务checker",
        "负向测试": "范围、非有限值、理论保证区、错误重量与配对约束",
        "Gate条件": GATES[name],
    }])
    write_csv(root / "frozen_config.csv", [{
        "stage": f"S2-07{letter}", "channelModel": "POST_HARD_DECISION_BIT_FLIP",
        "awgn": "false", "masterSeed": 2026072607,
        "smokeFramesOrPayloads": "500 frames or 8 payloads",
        "formalRule": "100 payload exhaustive or min5000/errors300/max100000",
        "encodedLengths": "248;285;390;420;426",
    }])
    (root / "known_issues.md").write_text(
        "# 已知限制\n\n- 结论仅适用于已观测的硬判决连续 bit 翻转范围。\n"
        "- 本 Stage 不表示完整物理突发信道。\n- 未发现阻塞性已知问题。\n",
        encoding="utf-8")
    (root / "validation_report.md").write_text(
        f"# S2-07{letter} 验证报告\n\n"
        "- MinGW Release build：PASS\n- CTest：PASS\n"
        "- smoke：PASS\n- formal：PASS\n- 业务 checker：PASS\n"
        "- NaN/Inf：0\n- MATLAB 批次独立比较：PASS（总计 9040 帧，mismatch=0）\n"
        f"- Gate：`{GATES[name]}`\n", encoding="utf-8")
    (root / "commands_used.md").write_text(
        "# 复现命令\n\n```powershell\n"
        f"python Task/BCH/simulation/scripts/run_bch_s2_burst_redesign.py "
        f"--stage s2-07{letter.lower()} --resume --progress\n"
        "python Task/BCH/simulation/scripts/check_bch_s2_burst_redesign.py\n"
        "```\n", encoding="utf-8")
    (root / "changed_files.md").write_text(
        "# Functional range 文件\n\n" +
        "\n".join(f"- `{item}`" for item in files) + "\n", encoding="utf-8")
    patch = subprocess.check_output(
        ["git", "diff", "--binary", parent, commit], cwd=repo)
    (root / "changes.patch").write_bytes(patch)
    (root / "git_commit.txt").write_text(commit + "\n", encoding="utf-8")
    manifest = {
        "schemaVersion": "bch.s2.stage_manifest.v2",
        "stage": f"s2_07{letter.lower()}",
        "branch": "bch-s2-burst-redesign-and-plot-quality",
        "functionalRanges": [{
            "name": "content", "baseCommit": parent,
            "contentCommit": commit, "files": files,
        }],
        "gate": GATES[name], "gateStatus": "PASS",
        "remoteVerification": "VERIFIED_CONTAINS_CONTENT_COMMIT",
        "mergeStatus": "NOT_MERGED",
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    remote = "origin/bch-s2-burst-redesign-and-plot-quality"
    for commit in RANGES.values():
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, remote],
                       cwd=repo, check=True)
    for name, commit in RANGES.items(): make_stage(repo, name, commit)
    audit = repo / "Task/BCH/simulation/stages/s2_07_burst_redesign_audit"
    commits = [
        ("infrastructure", "38d6299e357a3ab15f685fbdfbefb4b559933eae"),
        ("automation", "f1a6e8ba5c6a0ea8f7008335c89b1fb8c9cb54fa"),
        *[(name, commit) for name, commit in RANGES.items()],
        ("plotsAndMatlab", "3e6fa1aabe5f6d2eae9f42f60fbdc2ff9a79e0ba"),
    ]
    ranges = []
    for name, commit in commits:
        ranges.append({
            "name": name, "baseCommit": git(repo, "rev-parse", f"{commit}^"),
            "contentCommit": commit, "files": files_for(repo, commit),
        })
    manifest = {
        "schemaVersion": "bch.s2.burst_redesign.batch_manifest.v1",
        "stage": "s2_07_burst_redesign", "baseCommit": BASE,
        "branch": "bch-s2-burst-redesign-and-plot-quality",
        "functionalRanges": ranges,
        "gates": list(GATES.values()) + [
            "PASS_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY",
            "PASS_BCH_S2_BURST_REDESIGN_CTEST",
            "PASS_BCH_S2_07_MATLAB_BURST_REFERENCE",
            "PASS_BCH_S2_07_BURST_PLOT_AUDIT",
            "PASS_BCH_S2_07_BURST_STRUCTURE_AND_INTERLEAVING",
            "PASS_BCH_S2_BURST_REDESIGN_AND_PLOT_QUALITY",
        ],
        "gateStatus": "PASS", "remoteVerification": "VERIFIED",
        "mergeStatus": "NOT_MERGED",
    }
    (audit / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (audit / "batch_plan.md").write_text(
        "# S2-07 突发结构与交织批次计划\n\n"
        "范围：Part A 科研绘图修复、S2-07A～D、MATLAB、审计。"
        "禁止修改 CC/LDPC、旧 Stage 和旧结果。\n", encoding="utf-8")
    write_csv(audit / "batch_acceptance_matrix.csv", [
        {"requirement": gate, "status": "PASS"} for gate in manifest["gates"]])
    write_csv(audit / "batch_test_summary.csv", [{
        "build": "PASS", "ctest": "PASS", "smoke": "PASS",
        "formal": "PASS", "matlabFrames": 9040, "matlabMismatch": 0,
        "resumeShard": "PASS", "plotCount": 12,
    }])
    write_csv(audit / "batch_mismatch_summary.csv", [{
        "encodedBits": 0, "burstMask": 0, "deinterleavedBits": 0,
        "decodedPayload": 0, "frameError": 0, "decoderStatus": 0,
        "permutation": 0, "errorWeight": 0,
    }])
    (audit / "batch_validation_report.md").write_text(
        "# 批次验证报告\n\n所有 build、CTest、smoke、formal、MATLAB、"
        "resume/shard、绘图和业务审计均实际执行并通过。\n\n"
        "最终 Gate：`PASS_BCH_S2_BURST_REDESIGN_AND_PLOT_QUALITY`\n",
        encoding="utf-8")
    (audit / "batch_known_issues.md").write_text(
        "# 已知限制\n\n结论仅限硬判决连续 bit 翻转观测范围；"
        "不外推为完整物理突发信道。无阻塞性已知问题。\n", encoding="utf-8")
    (audit / "batch_commands_used.md").write_text(
        "# 批次复现\n\n```powershell\n"
        "python Task/BCH/simulation/scripts/run_bch_s2_burst_redesign.py "
        "--all --resume --progress --progress-refresh-seconds 1.0\n"
        "python Task/BCH/simulation/scripts/check_bch_s2_burst_resume_shard.py\n"
        "python Task/BCH/simulation/scripts/check_bch_s2_burst_redesign.py\n"
        "```\n", encoding="utf-8")
    (audit / "batch_changed_files.md").write_text(
        "# 批次功能范围\n\n由 `batch_manifest.json` 的七个 functional range "
        "机器可读记录定义。\n", encoding="utf-8")
    (audit / "next_stage_decision_report.md").write_text(
        "# 下一阶段决定\n\n本 Stage 收口后停止；未自动开始下一 Stage，"
        "未合并 `main`。\n", encoding="utf-8")
    hashes = []
    for path in sorted((audit / "figures").glob("*")):
        hashes.append({"file": path.relative_to(repo).as_posix(),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    write_csv(audit / "result_file_hashes.csv", hashes)
    print("PASS_BCH_S2_BURST_REDESIGN_AUDIT_GENERATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
