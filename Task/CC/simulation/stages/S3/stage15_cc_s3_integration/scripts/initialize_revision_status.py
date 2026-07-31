#!/usr/bin/env python3
"""Freeze the 2026-07-29 CC S3 revision specification and temporary Gate states."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[7]
S3 = SCRIPT.parents[2]
BASE = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, encoding="utf-8"
).strip()

SPECS = {
    "stage09_awgn_formal": {
        "status": "PARTIAL_PASS",
        "goal": "复核运行三种码率、硬/浮点软判决的两层 SNR 基线，重建 CI、来源和科研图。",
        "positive": "6 Case × 31 coarse 点满足 1000/200/50000，dense 来源可追溯。",
        "negative": "拒绝 200-bit formal、SNR 数学不一致、coarse/dense 来源混写。",
        "gate": "统一 SNR 字段、停止原因、CI、趋势与来源检查全部通过。",
    },
    "stage10_traceback_study": {
        "status": "PARTIAL_PASS",
        "goal": "扩展 R12/R23/R34、三个 FER 层级、六个 Dtb 与完整块参考，并自动推荐。",
        "positive": "63 个码率/层级/模式配置共享母数据且输出完整统计。",
        "negative": "拒绝缺 R34、手写 SNR、写死 D84 或缺联合真滑窗复核。",
        "gate": "正确性、最坏 FER 增幅、CI、四类推荐及 D84 联合复核通过。",
    },
    "stage11_soft_quantization": {
        "status": "PARTIAL_PASS",
        "goal": "完成三种码率、Q3～Q8/Float、clip 预扫、粗网格和候选 dense。",
        "positive": "651 个 coarse 点及候选 dense 具备 CI、分离裁剪计数和 SNR loss。",
        "negative": "拒绝 Q64 表示 Float、混合 saturationCount、缺 Q5/Q7/Q8/R34。",
        "gate": "完整网格、裁剪定义、SNR loss 和四类数据驱动推荐通过。",
    },
    "stage12_continuous_encoder": {
        "status": "PARTIAL_PASS",
        "goal": "强化 300、50×6、100×3、150×2 在三种码率下的连续状态与恢复回归。",
        "positive": "拼接码流/状态/打孔相位/最终尾比特及 checkpoint-resume 全一致。",
        "negative": "检测中间 slot 归零、加尾、打孔相位重启或恢复状态不一致。",
        "gate": "三种码率四种组织的所有回归均 PASS 后方可进入 Stage14。",
    },
    "stage13_sliding_window_viterbi": {
        "status": "BLOCKED",
        "goal": "实现实际 W×64 有界 survivor 缓存的 true_sliding_window_viterbi 并完成控制变量、自动选优和正式比较。",
        "positive": "W/S/D 分别控制缓存、推进和回溯；300 bit 恰好输出一次；正式曲线通过。",
        "negative": "拒绝 W<=D、S>W-D、完整 306 历史、丢失/重复 bit 与写死候选。",
        "gate": "算法单测、预扫、Pareto、多目标推荐、正式粗/dense 和完整块比较通过。",
    },
    "stage14_block_continuous_comparison": {
        "status": "BLOCKED",
        "goal": "实现四种组织、三码率的真实逐 slot 到达、在线滑窗触发和完整正式曲线。",
        "positive": "每 slot 到达即推进解码并记录 bit/source/decision 时标、边界、缓存、吞吐。",
        "negative": "拒绝完整 rx 拼接后一次 decode、错误时延公式或 Block 伪 boundaryBER=0。",
        "gate": "Stage12 先通过；372 coarse 点、候选 dense、在线证据和六类主图通过。",
    },
    "stage15_cc_s3_integration": {
        "status": "BLOCKED",
        "goal": "只读取通过 Gate 的正式数据，构建统一 scheme matrix、至少八张图和数据驱动推荐。",
        "positive": "同码率/同 SNR 公平对比，所有行具来源哈希，核心问题均给出数值。",
        "negative": "拒绝预扫/旧错误数据、不同 SNR 零散点直接比较或提前写死推荐。",
        "gate": "Stage09～14 全通过且 scheme matrix、图、文档、审计总 Gate 全通过。",
    },
}

COMMON = """\
## 公共冻结参数

- payloadBits = 300；K=7；生成多项式 171/133（八进制）；母码率 1/2；打孔码率 2/3、3/4。
- BPSK：0→+1，1→-1；横轴 `SNR = Es/N0 (dB)`。
- `sigmaSquared = 1/(2*10^(snrDb/10))`；`actualRate=payloadBits/transmittedBits`。
- `ebN0Db=snrDb-10*log10(actualRate)`；正式 CSV 记录 SNR、种子、case/sourceNoise、CI 和停止原因。
- coarse：-5～10 dB、0.5 dB；停止规则 1000/200/50000；dense 优先 0.1 dB。
- 只允许修改 `Task/CC/**`，禁止修改 BCH、LDPC、Common、main 或公共 SNR 定义。

## 非目标

- 不新增 200-bit 正式实验。
- 不把符号级离散 BPSK-AWGN 描述为连续波形仿真。
- 不合并 main，不删除旧 Stage，不用预扫描或旧错误结果冒充 formal。
"""


def write_stage(stage_name: str, spec: dict[str, str]) -> None:
    stage = S3 / stage_name
    plan = f"""# {stage_name} 2026-07-29 修订规格冻结

## 目标

{spec["goal"]}

{COMMON}
## 接口与数据

输入由 Stage09 正式基线、共享 payload/噪声标识和本 Stage 冻结配置组成；输出为原始 CSV、汇总 CSV、figure-data、PNG、plot manifest/check，以及可复现命令和审计文件。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 本 Stage 功能 | `{stage_name}/src` 与 `scripts` | {spec["positive"]} | {spec["negative"]} | {spec["gate"]} |
| 公平性与统计 | runner/checker | 同帧同噪声、CI、停止规则和 SNR 公式复算 | 篡改种子、缺字段、NaN/Inf、未覆盖插值 | checker 全通过 |
| 科研绘图 | `results` 与绘图脚本 | PNG/figure-data/hash 可复算 | 平滑、外推、零错误伪装非零 | plot check 全通过 |

## 当前临时状态

`{spec["status"]}`。只有本文件所列 Gate 实际通过后才更新最终状态。
"""
    (stage / "stage_plan.md").write_text(plan, encoding="utf-8")
    (stage / "validation_report.md").write_text(
        f"# {stage_name} 修订验证报告\n\n"
        f"- 基线 HEAD：`{BASE}`\n"
        f"- 当前状态：`{spec['status']}`\n"
        "- 旧结果归档：PASS\n"
        "- 功能实现与正式实验：尚在执行；不得据此宣称最终 PASS。\n",
        encoding="utf-8",
    )
    (stage / "known_issues.md").write_text(
        f"# {stage_name} 当前已知问题\n\n"
        f"- 临时状态：`{spec['status']}`。\n"
        f"- 尚未满足：{spec['gate']}\n"
        "- 本轮完成前不得用于 Stage15 最终结论。\n",
        encoding="utf-8",
    )
    manifest = {
        "stage": stage_name,
        "revision": "20260729_full_revision",
        "branch": "stage01-cc",
        "baseCommit": BASE,
        "functionalRanges": [],
        "allowedPaths": [f"Task/CC/simulation/stages/S3/{stage_name}/**"],
        "status": spec["status"],
        "gate": spec["gate"],
        "remoteVerification": "TO_VERIFY_AFTER_PUSH",
        "mergeStatus": "NOT_MERGED",
        "balancedWeights": (
            {
                "reliability": 0.35,
                "delay": 0.20,
                "memory": 0.20,
                "operations": 0.15,
                "cpuTime": 0.10,
            }
            if stage_name == "stage13_sliding_window_viterbi"
            else None
        ),
    }
    (stage / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"INITIALIZED {stage_name}: {spec['status']}")


def main() -> int:
    for stage_name, spec in SPECS.items():
        write_stage(stage_name, spec)
    print("PASS_CC_S3_REVISION_SPEC_FREEZE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
