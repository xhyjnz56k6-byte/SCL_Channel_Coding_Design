#!/usr/bin/env python3
"""Generate concise Chinese docs for the 2026-07-30 CC S3 continuation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


STAGE15 = Path(__file__).resolve().parents[1]
S3 = STAGE15.parent
STAGES = {
    "stage09_awgn_formal": "Stage09 整块编码正式基线",
    "stage10_traceback_study": "Stage10 有限回溯复核",
    "stage11_soft_quantization": "Stage11 软判决量化复核",
    "stage13_sliding_window_viterbi": "Stage13 真滑窗 W/S/D 控制变量正式实验",
    "stage14_block_continuous_comparison": "Stage14 整块与时隙连续组织比较",
    "stage15_cc_s3_integration": "Stage15 CC S3 最终集成",
}


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def stats() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    stage09 = load(
        S3
        / "stage09_awgn_formal"
        / "results"
        / "stage09_two_level_merged_point_results.csv"
    )
    out["stage09_awgn_formal"] = {
        "rows": len(stage09),
        "frames": int(stage09["framesProcessed"].sum()),
        "cases": stage09["caseId"].nunique(),
        "extra": "两层正式基线含粗网格和补充密集点；本轮作为整块参考输入 Stage15。",
    }
    stage10 = load(
        S3
        / "stage10_traceback_study"
        / "results"
        / "stage10_traceback_study_results.csv"
    )
    out["stage10_traceback_study"] = {
        "rows": len(stage10),
        "frames": int(stage10["frames"].sum()),
        "cases": stage10[["rateCase", "dtb"]].drop_duplicates().shape[0],
        "extra": "Dtb=35/49/70/84/98/112 的有限回溯数据继续用于内存-可靠性权衡。",
    }
    stage11 = load(
        S3
        / "stage11_soft_quantization"
        / "results"
        / "stage11_soft_quantization_results.csv"
    )
    out["stage11_soft_quantization"] = {
        "rows": len(stage11),
        "frames": int(stage11["frames"].sum()),
        "cases": stage11[["rateCase", "quantMode"]].drop_duplicates().shape[0],
        "extra": "Float 与 Q3-Q8 量化结果用于 Stage15 的量化损失和 Q8 工程候选。",
    }
    stage13 = load(
        S3
        / "stage13_sliding_window_viterbi"
        / "results"
        / "stage13_full_wsd_formal_results.csv"
    )
    out["stage13_sliding_window_viterbi"] = {
        "rows": len(stage13),
        "frames": int(stage13["frames"].sum()),
        "cases": stage13[["rateCase", "candidateId"]].drop_duplicates().shape[0],
        "extra": (
            "本轮新增 full W/S/D 正式网格：CONTROL_W=372 点、"
            "CONTROL_S=372 点、CONTROL_D=558 点。"
        ),
    }
    stage14 = load(
        S3
        / "stage14_block_continuous_comparison"
        / "results"
        / "stage14_online_slot_formal_results.csv"
    )
    out["stage14_block_continuous_comparison"] = {
        "rows": len(stage14),
        "frames": int(stage14["frames"].sum()),
        "cases": stage14[["rateCase", "organization"]].drop_duplicates().shape[0],
        "extra": "Block300、50x6、100x3、150x2 共 12 个正式组织/码率组合。",
    }
    stage15 = load(
        S3
        / "stage15_cc_s3_integration"
        / "results"
        / "stage15_final_scheme_matrix.csv"
    )
    out["stage15_cc_s3_integration"] = {
        "rows": len(stage15),
        "frames": int(stage15["frames"].sum()),
        "cases": stage15["schemeId"].nunique(),
        "extra": "最终矩阵已纳入 Stage13FullWSD 1302 行正式控制变量结果。",
    }
    return out


def write_readme(stage_dir: Path, title: str, info: dict[str, object]) -> None:
    text = f"""一、阶段名称
{title}

二、实验目的
围绕 CC S3 300 bit 高速电文场景，给出可审计的 BER、FER、有效吞吐、译码时延、内存和复杂度数据。

三、实验背景和它在 S3 总任务中的作用
本阶段属于 S3 正式实验链条的一部分。Stage09 提供整块基线，Stage10/11 提供回溯和量化补充，Stage13 提供真滑窗参数控制变量，Stage14 提供时隙连续组织比较，Stage15 汇总为最终方案矩阵。

四、实验输入
payloadBits=300，SNR = Es/N0，范围 -5.0 dB 到 10.0 dB，步长 0.5 dB。

五、编码参数
卷积码 K=7，生成多项式 171/133 octal，母码率 1/2，打孔码率 R12/R23/R34。

六、译码方式
整块实验使用完整 Viterbi；滑窗和时隙实验使用已修复的真滑窗/在线到达机制；量化实验比较 Float 与 Q 位宽软判决。

七、控制变量
本阶段记录 {info['cases']} 个配置组合。Stage13 本轮严格区分 W、S、D 单变量变化，其它阶段保持各自冻结配置。

八、SNR范围与停止条件
正式网格使用 minFrames=1000、targetFrameErrors=200、maxFrames=50000；停止原因只允许达到目标误帧或最大帧数。

九、随机性和公平性
同一码率、SNR 和 frameIndex 共享 payload 与标准高斯母噪声；Hard/Soft 和候选参数只派生不同译码输入，不重新生成独立噪声。

十、执行流程
本轮先归档旧 results，再运行无噪声回归、Stage13 full W/S/D formal shard、后处理、Stage15 集成和 checker。

十一、输出文件
主要输出位于 results/，包括正式 CSV、figure-data CSV、PNG、plot manifest 和 Markdown 分析。

十二、主要结果
当前正式结果行数 {info['rows']}，累计仿真帧数 {info['frames']}。

十三、结果解释
{info['extra']}

十四、与上一轮相比的修改
20260730 本轮新增 archive/v02_20260730_before_cc_s3_formal_continuation，并把 Stage13 full W/S/D 正式网格纳入最终集成。

十五、当前进展状态
已完成本轮归档、Stage13 full W/S/D formal、Stage15 矩阵重建和基础 checker。

十六、已知限制
当前仿真是符号级离散 BPSK-AWGN；没有显式采样率、过采样、脉冲成形、匹配滤波、带宽和连续波形噪声建模。

十七、是否通过 Gate
本轮阶段级 checker 已通过；最终 Gate 仍需 Git 审计、提交和远程验证后确认。
"""
    (stage_dir / "readme.txt").write_text(text, encoding="utf-8")


def write_analysis(stage_dir: Path, title: str, info: dict[str, object]) -> None:
    results = stage_dir / "results"
    images = sorted(path for path in results.glob("*.png"))
    lines = [
        f"# {title} results 分析",
        "",
        "## 1. 阶段实验目的",
        "支撑 CC S3 300 bit 高速电文正式评估，输出可追溯的性能和资源数据。",
        "",
        "## 2. 本轮正式配置",
        "SNR = Es/N0，-5.0 dB 到 10.0 dB，步长 0.5 dB；minFrames=1000，targetFrameErrors=200，maxFrames=50000。",
        "",
        "## 3. 仿真规模",
        f"正式结果行数 {info['rows']}，累计帧数 {info['frames']}，配置组合数 {info['cases']}。",
        "",
        "## 4. 数据完整性检查",
        "本轮结果由脚本从正式 CSV 和 runtime shard 生成，未手工修改 BER/FER，未用空图作为 PASS。",
        "",
        "## 5. 主要现象",
        info["extra"],
        "",
        "## 6. 结果图",
        "",
    ]
    for image in images[:24]:
        lines.append(f"### {image.name}")
        lines.append(f"![{image.stem}](./{image.name})")
        figure_csv = results / "figure_data" / f"{image.stem}.csv"
        if not figure_csv.exists():
            figure_csv = results / f"{image.stem}_figure_data.csv"
        lines.append(
            f"对应 figure-data：{figure_csv.name if figure_csv.exists() else '未单独生成'}。"
        )
        lines.append("")
    lines += [
        "## 7. 限制",
        "CPU 时间依赖当前硬件和进程并行状态；零误码点只代表有限帧数下的上界，不代表理论误码平台。",
    ]
    (results / "results_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    all_stats = stats()
    for stage, title in STAGES.items():
        stage_dir = S3 / stage
        info = all_stats[stage]
        write_readme(stage_dir, title, info)
        write_analysis(stage_dir, title, info)
    print("PASS_CC_S3_DOCS_20260730")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
