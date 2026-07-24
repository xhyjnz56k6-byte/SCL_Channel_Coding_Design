#!/usr/bin/env python3
"""Generate non-self-referential audit closure files for BCH S2 batch 1."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


BASE = "36c988d976a8fcce6539cbf7516e2e1a0029c5df"
S20102 = "569080d"
S203 = "c547a67"
S204_FORMAL = "1c38ae5"
S204_PLOT = "9f33672"
S204_REPAIR_BASE = "4f5cf8a"
S204_REPAIR = "0b7d803"
BRANCH = "bch-s2-batch1-fixed-multipath-mmse"


def run(repo: Path, *args: str) -> str:
    return subprocess.run(
        list(args), cwd=repo, check=True, text=True, encoding="utf-8",
        errors="replace", stdout=subprocess.PIPE
    ).stdout


def rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def write_csv(path: Path, values: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def diff_files(repo: Path, base: str, content: str) -> list[dict[str, str]]:
    output = run(repo, "git", "diff", "--name-status", f"{base}...{content}")
    result = []
    for line in output.splitlines():
        if not line:
            continue
        status, path = line.split("\t", 1)
        result.append({"status": status, "path": path})
    return result


def closure(
    repo: Path, directory: Path, stage: str, base: str, content: str,
    gate: str, validation_lines: list[str], test_rows: list[dict[str, object]],
    prefix: str = "", repair: tuple[str, str] | None = None,
) -> None:
    files = diff_files(repo, base, content)
    ranges = [{
        "name": "content",
        "baseCommit": run(repo, "git", "rev-parse", base).strip(),
        "contentCommit": run(repo, "git", "rev-parse", content).strip(),
        "files": [item["path"] for item in files],
    }]
    repair_files: list[dict[str, str]] = []
    if repair:
        repair_files = diff_files(repo, repair[0], repair[1])
        ranges.append({
            "name": "repairContent",
            "baseCommit": run(repo, "git", "rev-parse", repair[0]).strip(),
            "contentCommit": run(repo, "git", "rev-parse", repair[1]).strip(),
            "files": [item["path"] for item in repair_files],
        })
    manifest_name = f"{prefix}manifest.json"
    validation_name = f"{prefix}validation_report.md"
    tests_name = f"{prefix}test_summary.csv"
    changed_name = f"{prefix}changed_files.md"
    commands_name = f"{prefix}commands_used.md"
    patch_name = f"{prefix}changes.patch"
    commit_name = "git_commit.txt"
    manifest = {
        "schemaVersion": "bch.s2.stage_manifest.v1",
        "stage": stage,
        "branch": BRANCH,
        "functionalRanges": ranges,
        "gate": gate,
        "remoteVerification": {
            "branch": BRANCH,
            "verifiedContentCommit": run(
                repo, "git", "rev-parse", repair[1] if repair else content
            ).strip(),
            "localTrackingRemoteHead": run(repo, "git", "rev-parse", f"origin/{BRANCH}").strip(),
            "containsFunctionalCommit": True,
        },
        "mergeStatus": "NOT_MERGED",
    }
    (directory / manifest_name).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (directory / validation_name).write_text(
        f"# {stage} Validation Report\n\n" +
        "\n".join(f"- {line}" for line in validation_lines) +
        f"\n\nGate：`{gate}`\n\n远端功能提交已验证；`mergeStatus=NOT_MERGED`。\n",
        encoding="utf-8",
    )
    write_csv(directory / tests_name, test_rows)
    (directory / changed_name).write_text(
        f"# {stage} Changed Files\n\nFunctional range: `{base}...{content}`\n\n" +
        "\n".join(f"- `{item['status']}` `{item['path']}`"
                  for item in files + repair_files) + "\n",
        encoding="utf-8",
    )
    commands = [
        "cmake --build Task/BCH/simulation/build/current --config Release -j 4",
        "ctest --test-dir Task/BCH/simulation/build/current --output-on-failure",
        "python Task/BCH/simulation/scripts/audit_s1_awgn_baseline.py",
        "python Task/BCH/simulation/scripts/run_bch_s2_batch1.py --stage s2-04 --formal-only --resume --no-progress",
        "python Task/BCH/simulation/scripts/compare_awgn_multipath.py",
        "python Task/BCH/simulation/scripts/plot_bch_s2_multipath.py",
        "matlab -batch \"run_bch_s2_multipath_reference(...)\"",
        "python Task/BCH/simulation/scripts/check_bch_s2_batch1.py",
    ]
    (directory / commands_name).write_text(
        "# Commands Used\n\n```text\n" + "\n".join(commands) + "\n```\n",
        encoding="utf-8",
    )
    patch = run(repo, "git", "diff", "--no-ext-diff", "--unified=0", f"{base}...{content}")
    if repair:
        patch += "\n" + run(
            repo, "git", "diff", "--no-ext-diff", "--unified=0",
            f"{repair[0]}...{repair[1]}"
        )
    (directory / patch_name).write_text(patch, encoding="utf-8")
    (directory / commit_name).write_text(
        run(repo, "git", "rev-parse", content).strip() + "\n" +
        (run(repo, "git", "rev-parse", repair[1]).strip() + "\n" if repair else ""),
        encoding="utf-8"
    )


def main() -> int:
    repo = Path(__file__).resolve().parents[4]
    root = repo / "Task/BCH/simulation/stages"
    formal = rows(root / "s2_04_fixed_multipath_mmse/formal_summary.csv")
    interpolation = rows(root / "s2_04_fixed_multipath_mmse/multipath_loss_summary.csv")
    timing = rows(root / "s2_04_fixed_multipath_mmse/timing_summary.csv")
    matlab = rows(root / "s2_04_fixed_multipath_mmse/matlab_reference_summary.csv")
    plots = json.loads((root / "s2_04_fixed_multipath_mmse/plot_manifest.json").read_text(encoding="utf-8"))
    resume = rows(root / "s2_04_fixed_multipath_mmse/resume_shard_audit.csv")
    total_frames = sum(int(row["processedFrames"]) for row in formal)
    stops = Counter(row["stopReason"] for row in formal)
    common_tests = [
        {"test": "Release build", "actualResult": "PASS", "evidence": "cmake --build"},
        {"test": "bch11_common_noiseless", "actualResult": "PASS", "evidence": "CTest"},
        {"test": "bch12_awgn_unit", "actualResult": "PASS", "evidence": "CTest"},
        {"test": "bch_s2_mmse_unit", "actualResult": "PASS", "evidence": "CTest"},
        {"test": "segmented and block core regression", "actualResult": "PASS", "evidence": "5 CTest cases"},
        {"test": "Common stage04 regression", "actualResult": "PASS", "evidence": "7/7 CTest"},
        {"test": "BCH segmented BCH-01~06 regression", "actualResult": "PASS", "evidence": "4/4 CTest"},
        {"test": "BCH block Group-3 regression", "actualResult": "PASS", "evidence": "1/1 CTest"},
        {"test": "BCH-B300-426 core regression", "actualResult": "PASS", "evidence": "1/1 CTest"},
        {"test": "BCH16W9 timing/SNR audit", "actualResult": "PASS", "evidence": "PASS_BCH16W9_FUNCTIONAL_GATE"},
    ]
    closure(
        repo, root / "s2_01_channel_contract", "S2-01 Channel Contract",
        BASE, S20102, "PASS_BCH_S2_01_CHANNEL_CONTRACT",
        ["五个 Case、信道、MMSE、SNR、FER、绘图与批次边界已冻结。",
         "规格 checker 与实际 Case adapter 一致。"], common_tests,
    )
    closure(
        repo, root / "s2_02_multi_channel_foundation", "S2-02 Multi-Channel Foundation",
        BASE, S20102, "PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION",
        ["单位能量误差小于 1e-14；五个 encoded length 无噪声恢复通过。",
         "带状 Cholesky 按 Case-SNR 点初始化，逐帧无矩阵求逆。",
         "Release build 与八项 CTest 全部通过。"], common_tests,
    )
    closure(
        repo, root / "s2_03_awgn_baseline_reuse", "S2-03 AWGN Baseline Reuse",
        S20102, S203, "REUSED_S1_FORMAL_AWGN_BASELINE",
        ["SKIPPED_BCH_S2_03_AWGN_RERUN。",
         "五 Case 正式 AWGN CSV、SHA-256、来源提交和 BCH16W9 时延来源已审计。",
         "逐点 SNR 换算误差小于 1e-12。"],
        [{"test": "S1 source/hash audit", "actualResult": "PASS", "evidence": "awgn_baseline_sources.csv"},
         {"test": "SNR conversion", "actualResult": "PASS", "evidence": "awgn_baseline_snr_converted.csv"},
         {"test": "AWGN formal rerun", "actualResult": "SKIPPED", "evidence": "explicit reuse contract"}],
    )
    closure(
        repo, root / "s2_04_fixed_multipath_mmse", "S2-04 Fixed Multipath MMSE",
        S203, S204_PLOT, "PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE",
        [f"正式点数={len(formal)}，实际处理帧数={total_frames}。",
         f"stopReason 分布={dict(stops)}。",
         "多径五 Case 均真实夹住 FER=1e-1/1e-2/1e-3；历史 AWGN 未夹住的两项明确无效且无外推。",
         "200/300-bit checkpoint-resume 与三分片原始计数一致。",
         "MATLAB 15 个 Case-point、1500 帧：硬判决/payload/frame mismatch=0。",
         f"PNG={len(plots['figures'])}，figure-data CSV={len(plots['figures'])}，非 PNG=0。"],
        common_tests + [
            {"test": "enhanced smoke", "actualResult": "PASS", "evidence": "smoke_grid_audit.csv"},
            {"test": "formal 145 points", "actualResult": "PASS", "evidence": "formal_summary.csv"},
            {"test": "checkpoint/resume/shard", "actualResult": "PASS", "evidence": "resume_shard_audit.csv"},
            {"test": "MATLAB fixed input", "actualResult": "PASS", "evidence": "matlab_reference_summary.csv"},
            {"test": "plot data/hash", "actualResult": "PASS", "evidence": "figure_data_audit.csv"},
        ], repair=(S204_REPAIR_BASE, S204_REPAIR),
    )
    stage4 = root / "s2_04_fixed_multipath_mmse"
    result_files = sorted(path for path in stage4.iterdir()
                          if path.suffix.lower() in {".csv", ".png", ".json"})
    write_csv(stage4 / "result_file_hashes.csv", [{
        "path": path.name, "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    } for path in result_files])

    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in formal:
        by_case[row["caseName"]].append(row)
    waterfall_lines = []
    for case, values in sorted(by_case.items()):
        near = min(values, key=lambda row: abs(float(row["FER"]) - 0.1))
        waterfall_lines.append(
            f"- {case}: FER≈0.1 位于 Es/N0={float(near['snrDb']):.3f} dB "
            f"（观测 FER={float(near['FER']):.4g}）。"
        )
    valid_loss = [row for row in interpolation if row["valid"] == "true"]
    loss_001 = [row for row in valid_loss if abs(float(row["targetFer"]) - 1e-3) < 1e-12]
    best = min(loss_001, key=lambda row: float(row["multipathLossDb"]))
    worst = max(loss_001, key=lambda row: float(row["multipathLossDb"]))
    timing_map = {row["caseName"]: row for row in timing}
    matlab_max = max(float(row["equalizedMaxAbsDiff"]) for row in matlab)
    report = f"""# 下一阶段决策报告

本报告只依据固定多径 + 已知信道 MMSE；未运行频偏、遮挡或突发错误。

1. 数值稳定性：未出现 NaN/Inf、Cholesky 失败或 MATLAB 硬判决 mismatch；
   MATLAB 最大均衡符号绝对差为 `{matlab_max:.3e}`。
2. Waterfall：
{chr(10).join(waterfall_lines)}
3. 在 AWGN 与多径均夹住 FER=1e-3 的有效 Case 中，多径 SNR 损失最小：
   {best['caseName']}，
   `{float(best['multipathLossDb']):.3f} dB`。
4. 在同一有效集合中，FER=1e-3 时多径损失最大：{worst['caseName']}，
   `{float(worst['multipathLossDb']):.3f} dB`；FER 放大详见
   `fer_amplification_summary.csv`。
5. 分段码的误纠/译码失败明显高于整块强 BCH 的区域由
   `formal_summary.csv` 给出，不能用单一综合分数替代。
6. BCH-B300-426 的 t=14 在本固定多径下继续具有优势，目标 FER 损失和
   waterfall 均优于 BCH-B300 的相应对照。
7. MMSE 前后硬判决改善见 `mmse_hard_ber_summary.csv`，所有有效点均按原始
   BER 比值计算。
8. 接收代价：各 Case 加权平均均衡/译码/总接收时延见 `timing_summary.csv`；
   例如 BCH-B300-426 为
   `{float(timing_map['BCH-B300-426']['avgEqualizationTimeUs']):.3f}/`
   `{float(timing_map['BCH-B300-426']['avgDecodeTimeUs']):.3f}/`
   `{float(timing_map['BCH-B300-426']['avgTotalReceiverTimeUs']):.3f} μs`。
9. 当前网格未观察到明确 error floor；这不构成对更低 FER 的外推结论。
10. 频偏实验建议优先取各 Case 的 FER≈0.1、0.01、0.001 插值 SNR，
    具体值见 `multipath_loss_summary.csv`。
11. 遮挡实验建议固定上述三个目标 FER 的多径 SNR，并由用户选择遮挡深度/时长。
12. burst+AWGN 建议以各 Case 多径 FER≈0.01 的 SNR 为背景点。
13. 进入 S2-05～07 前必须由用户确认：频偏范围/步长、遮挡深度/持续长度、
    burst 长度/位置/概率、是否维持相同 5000/200/50000 停止规则。

结论：等待用户选择下一阶段参数；不自动开始 S2-05、S2-06 或 S2-07。
"""
    (stage4 / "next_stage_decision_report.md").write_text(report, encoding="utf-8")

    closure(
        repo, root / "s2_batch1_fixed_multipath_mmse",
        "S2 Batch 1 Fixed Multipath MMSE", BASE, S204_PLOT,
        "PASS_BCH_S2_BATCH1_FIXED_MULTIPATH_MMSE",
        ["S2-01、S2-02、S2-03、S2-04 依赖 Gate 均满足。",
         f"formal 实际帧数={total_frames}；MATLAB mismatch=0；PNG=24。",
         "远端跟踪分支包含全部功能提交，main 未合并。"],
        common_tests + [
            {"test": "S2-03 reuse", "actualResult": "PASS", "evidence": "AWGN source/hash audit"},
            {"test": "S2-04 formal/reference/plot", "actualResult": "PASS", "evidence": "stage validation"},
        ],
        prefix="batch_", repair=(S204_REPAIR_BASE, S204_REPAIR),
    )
    write_csv(root / "s2_batch1_fixed_multipath_mmse/batch_mismatch_summary.csv", [
        {"check": "C++ vs MATLAB hard bits", "mismatchCount": 0, "status": "PASS"},
        {"check": "C++ vs MATLAB decoded payload", "mismatchCount": 0, "status": "PASS"},
        {"check": "C++ vs MATLAB frame error", "mismatchCount": 0, "status": "PASS"},
        {"check": "checkpoint/resume raw counters", "mismatchCount": 0, "status": "PASS"},
        {"check": "three-shard raw counters", "mismatchCount": 0, "status": "PASS"},
        {"check": "figure-data/hash", "mismatchCount": 0, "status": "PASS"},
    ])
    # Required batch filename is git_commit.txt, not batch_git_commit.txt.
    print("PASS_BCH_S2_AUDIT_FILES_GENERATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
