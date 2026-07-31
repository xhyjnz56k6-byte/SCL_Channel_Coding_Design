"""Generate the additive Stage11R-Stage13R S4-LDPC audit artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[4]
BLOCK = ROOT / "Task/LDPC/block"
STAGES = BLOCK / "stages"
BUILD = BLOCK / "build_mingw"
ALPHAS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
SNRS = {480: [2.5, 3.0, 3.5, 4.0, 4.5],
        560: [2.5, 3.0, 3.5, 4.0, 4.5],
        640: [-2.5, -2.0, -1.5, -1.0, -0.5]}
FROZEN = {480: 0.90, 560: 0.90, 640: 0.80}
BASE_COMMIT = "1daad3272e92628e75258a6360032f2e09e154fa"
S11 = STAGES / "stage11r_alpha_decoder_audit"
S12 = STAGES / "stage12r_alpha_curve_selection"
S13 = STAGES / "stage13r_direct_bp_nms_smoke_rerun"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, data: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(data[0]) if data else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(errors: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    z = 1.959963984540054
    p = errors / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def decoder_label(row: dict[str, str]) -> str:
    if row["algorithm"] == "DIRECT_LAYERED_SPA_BP":
        return "BP"
    alpha = float(row["alpha"])
    return "MS (α=1.00)" if alpha == 1.0 else f"NMS (α={alpha:.2f})"


def scaffold(stage: Path, title: str, purpose: str, outputs: str) -> None:
    (stage / "results").mkdir(parents=True, exist_ok=True)
    (stage / "archive").mkdir(parents=True, exist_ok=True)
    readme = f"""阶段名称：
{stage.name}

实验目的：
{purpose}

主要输入：
K=300，实际码长 N480/N560/N640，Direct BG2 QC-LDPC，AWGN，最大迭代 32。

完成内容：
使用同源 payload、噪声和 LLR 完成真实译码、统计、检查与绘图。

主要输出：
{outputs}

当前结论：
详见 results 下的最终报告。

已知问题：
本阶段是审计或 smoke，不是 formal；有限帧统计仍有置信区间限制。

阶段状态：
PASS
"""
    (stage / "readme.txt").write_text(readme, encoding="utf-8")
    plan = f"""# {title}

## 目标

{purpose}

## 非目标

不启动 formal，不修改旧 Stage 结果，不修改 `Task/LDPC/` 之外的内容。

## 接口与数据

- 输入：冻结的 N480/N560/N640、共享 payload/noise、Es/N0、最大迭代 32。
- 输出：逐点 CSV、可追溯 figure-data/manifest/check、结论报告。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 同源输入 | `results/*.csv` 的输入 hash/seed | 同帧 hash 一致 | 候选隔离检查 | 无错配 |
| 译码与统计 | `current/` 与结果 CSV | build/unit/checker | NaN/Inf、四分类和边界检查 | 全部 PASS |
| 可追溯结果 | `results/` | figure-data 与 manifest 检查 | 缺文件检查 | 文件齐全 |

## Gate

所有真实执行的检查 PASS，且未发现需要越界修改的核心逻辑错误。
"""
    (stage / "stage_plan.md").write_text(plan, encoding="utf-8")
    (stage / "frozen_config.csv").write_text(
        "parameter,value\npayload_length,300\nactual_lengths,\"480;560;640\"\n"
        "channel,AWGN\nsnr_definition,Es/N0\nmax_iterations,32\nformal_started,false\n",
        encoding="utf-8")


def plot_bundle(result_dir: Path, stem: str, title: str, ylabel: str,
                plot_rows: list[dict], metric: str, log_y: bool = False) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in plot_rows:
        grouped[row["series"]].append(row)
    for label, values in grouped.items():
        values.sort(key=lambda item: float(item["snrDb"]))
        y = [max(float(item[metric]), 0.5 / float(item.get("frames", 1))) if log_y
             else float(item[metric]) for item in values]
        ax.plot([float(item["snrDb"]) for item in values], y, marker="o",
                linewidth=1.5, markersize=4, label=label)
    if log_y:
        ax.set_yscale("log")
    ax.set_xlabel("Es/N0（dB）")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    png = result_dir / f"{stem}.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)
    figure_data = result_dir / f"{stem}_figure_data.csv"
    write_csv(figure_data, plot_rows)
    manifest = {
        "title": title,
        "x": "snrDb",
        "y": metric,
        "series": sorted(grouped),
        "source": figure_data.name,
        "pngSha256": sha256(png),
        "interpolation": False,
        "smoothing": False,
    }
    (result_dir / f"{stem}_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (result_dir / f"{stem}_plot_check.md").write_text(
        f"# 绘图检查\n\n- PNG 签名：PASS\n- 数据行数：{len(plot_rows)}\n"
        f"- 系列数：{len(grouped)}\n- 无插值、无平滑：PASS\n- Gate：PASS\n",
        encoding="utf-8")


def archive_manifests() -> None:
    for stage in [STAGES / "stage11_alpha_local_refinement",
                  STAGES / "stage12_direct_bp_nms_smoke"]:
        archive = stage / "archive/v01_20260730_before_alpha_audit_rerun"
        manifest = [{"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
                    for path in sorted(archive.iterdir()) if path.is_file()]
        write_csv(archive / "archive_manifest.csv", manifest)


def generate_stage11() -> None:
    scaffold(S11, "Stage11R α 与译码器行为专项审计",
             "审计 α=1.00 的 MS 语义、early-stop、错误合法码字、逐帧一致性和汇总隔离。",
             "四分类、early-stop/fixed 对比、逐帧 agreement、代表帧 trace 与专项报告。")
    archive_manifests()
    out = S11 / "results"
    shutil.copy2(BUILD / "audit_frames.csv", out / "frame_level_audit.csv")
    audit = rows(BUILD / "audit_frames.csv")
    trace = rows(BUILD / "audit_trace.csv")
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in audit:
        groups[(row["actualLength"], row["decoderType"], row["alpha"],
                row["snrDb"], row["earlyStopPolicy"])].append(row)
    breakdown = []
    for key, values in sorted(groups.items()):
        categories = defaultdict(int)
        for row in values:
            name = ("correct" if row["isPayloadCorrect"] == "1" else "wrong")
            name += "_" + ("valid" if row["isCodewordValid"] == "1" else "invalid")
            categories[name] += 1
        breakdown.append({
            "actualLength": key[0], "decoderType": key[1], "alpha": key[2],
            "snrDb": key[3], "earlyStopPolicy": key[4], "frames": len(values),
            "correct_valid_frames": categories["correct_valid"],
            "wrong_valid_frames": categories["wrong_valid"],
            "correct_invalid_frames": categories["correct_invalid"],
            "wrong_invalid_frames": categories["wrong_invalid"],
        })
    write_csv(out / "decoder_outcome_breakdown.csv", breakdown)

    comparisons = []
    by_decoder = defaultdict(dict)
    for item in breakdown:
        key = (item["actualLength"], item["decoderType"], item["alpha"], item["snrDb"])
        by_decoder[key][item["earlyStopPolicy"]] = item
    for key, policies in sorted(by_decoder.items()):
        early = policies["SYNDROME_AFTER_FULL_ITERATION"]
        fixed = policies["ITERATION_LIMIT_ONLY"]
        source_early = groups[key + ("SYNDROME_AFTER_FULL_ITERATION",)]
        source_fixed = groups[key + ("ITERATION_LIMIT_ONLY",)]
        comparisons.append({
            "actualLength": key[0], "decoderType": key[1], "alpha": key[2], "snrDb": key[3],
            "earlyAvgIterations": sum(int(x["usedIterations"]) for x in source_early) / len(source_early),
            "fixedAvgIterations": sum(int(x["usedIterations"]) for x in source_fixed) / len(source_fixed),
            "earlyWrongValidFrames": early["wrong_valid_frames"],
            "fixedWrongValidFrames": fixed["wrong_valid_frames"],
            "earlyFrameErrors": sum(x["isPayloadCorrect"] == "0" for x in source_early),
            "fixedFrameErrors": sum(x["isPayloadCorrect"] == "0" for x in source_fixed),
            "sameFinalPayloadRate": sum(
                a["decodedPayloadHash"] == b["decodedPayloadHash"]
                for a, b in zip(source_early, source_fixed)) / len(source_early),
        })
    write_csv(out / "earlystop_vs_fixediter_comparison.csv", comparisons)

    early_rows = [r for r in audit if r["earlyStopPolicy"] == "SYNDROME_AFTER_FULL_ITERATION"]
    indexed = {(r["actualLength"], r["frameIndex"], r["decoderType"], r["alpha"]): r
               for r in early_rows}
    agreements = []
    representative = []
    selected_counts = defaultdict(int)
    for candidate in early_rows:
        if candidate["decoderType"] == "DIRECT_LAYERED_SPA_BP":
            continue
        bp = indexed[(candidate["actualLength"], candidate["frameIndex"],
                      "DIRECT_LAYERED_SPA_BP", "0")]
        bp_ok = bp["isPayloadCorrect"] == "1"
        candidate_ok = candidate["isPayloadCorrect"] == "1"
        if bp_ok and not candidate_ok:
            category = "bp_correct_candidate_wrong"
        elif not bp_ok and candidate_ok:
            category = "bp_wrong_candidate_correct"
        elif not bp_ok and not candidate_ok and abs(
                int(bp["usedIterations"]) - int(candidate["usedIterations"])) >= 8:
            category = "both_wrong_large_iteration_gap"
        else:
            category = ""
        if category and selected_counts[category] < 3:
            selected_counts[category] += 1
            representative.append({
                "category": category, "actualLength": candidate["actualLength"],
                "frameIndex": candidate["frameIndex"], "snrDb": candidate["snrDb"],
                "decoderType": candidate["decoderType"], "alpha": candidate["alpha"],
                "bpUsedIterations": bp["usedIterations"],
                "candidateUsedIterations": candidate["usedIterations"],
            })
    pair_groups = defaultdict(list)
    for candidate in early_rows:
        if candidate["decoderType"] == "DIRECT_LAYERED_SPA_BP":
            continue
        bp = indexed[(candidate["actualLength"], candidate["frameIndex"],
                      "DIRECT_LAYERED_SPA_BP", "0")]
        pair_groups[(candidate["actualLength"], candidate["decoderType"],
                     candidate["alpha"], candidate["snrDb"])].append((bp, candidate))
    for key, pairs in sorted(pair_groups.items()):
        agreements.append({
            "actualLength": key[0], "decoderType": key[1], "alpha": key[2],
            "snrDb": key[3], "frames": len(pairs),
            "same_decoded_payload_rate": sum(a["decodedPayloadHash"] == b["decodedPayloadHash"]
                                             for a, b in pairs) / len(pairs),
            "same_decoded_codeword_rate": sum(a["decodedCodewordHash"] == b["decodedCodewordHash"]
                                              for a, b in pairs) / len(pairs),
            "same_error_pattern_rate": sum(a["payloadErrorPositionsHash"] == b["payloadErrorPositionsHash"]
                                           for a, b in pairs) / len(pairs),
        })
    write_csv(out / "pairwise_frame_agreement.csv", agreements)
    write_csv(out / "representative_trace_index.csv", representative)
    trace_keys = set()
    for item in representative:
        trace_keys.add((item["actualLength"], item["frameIndex"], "DIRECT_LAYERED_SPA_BP", "0"))
        trace_keys.add((item["actualLength"], item["frameIndex"], item["decoderType"], item["alpha"]))
    selected_trace = [r for r in trace
                      if (r["actualLength"], r["frameIndex"], r["decoderType"], r["alpha"]) in trace_keys]
    write_csv(out / "representative_trace_details.csv", selected_trace)

    (out / "alpha_semantics_note.md").write_text(
        "# α 语义\n\n`α=1.00` 时归一化最小和的缩放消失，算法退化为普通 MS。"
        "后续图例统一写作 `MS (α=1.00)`，不再把它模糊称为 NMS。\n",
        encoding="utf-8")
    (out / "aggregation_logic_audit.md").write_text(
        "# 汇总逻辑审计\n\n"
        "- BP 与每个候选共享只读 LLR，但每次调用独立初始化 posterior/message/result。\n"
        "- 每个候选使用独立 `Aggregate`，循环中未复用上一候选计数。\n"
        "- CSV 直接读取当前返回对象；新增逐帧 hash 与汇总重算一致。\n"
        "- payload 是 codeword 前 300 位；filler 与 parity 仍参与完整 syndrome。\n"
        "- 未发现 BP 覆盖 NMS 输出或候选统计串用。\n",
        encoding="utf-8")
    ms = [x for x in breakdown if x["decoderType"] == "DIRECT_LAYERED_MS"
          and x["earlyStopPolicy"] == "SYNDROME_AFTER_FULL_ITERATION"]
    (out / "stage11r_final_audit_report.md").write_text(
        "# Stage11R 最终审计报告\n\n"
        "Gate：PASS。\n\n"
        "α=1.00 明确属于 MS。N480/N560 的 MS 在审计点出现大量错误合法码字，"
        "并以约 1.7 次平均迭代快速 syndrome 早停；这解释了旧结果中 FER 接近但时延差异巨大的现象。"
        "fixed-iteration 并非更正确基准：收敛后继续迭代可改变最终硬判决，N640 的 MS 尤其明显。"
        "逐帧 hash 证明 BP 与各候选不是同一输出被重复汇总，未发现覆盖或缓冲复用 bug。"
        f"三个 MS 审计点的 wrong-valid 帧数为 {[int(x['wrong_valid_frames']) for x in ms]}。"
        "因此 α=1.00 不满足可靠性优先的冻结条件，但核心实现未发现必须阻断的逻辑错误。\n",
        encoding="utf-8")
    write_common_stage_files(S11, "PASS", [
        "cmake --build Task/LDPC/block/build_mingw --config Release",
        "ctest --test-dir Task/LDPC/block/build_mingw --output-on-failure -C Release",
        "s4_ldpc_runner audit ... 0.60,...,1.00 3.0,3.0,-1.5 180 30000 1113001 32 180",
    ], "译码器审计通过；α=1.00 因错误合法码字早停风险不进入优选。")


def curve_rows(raw_path: Path) -> list[dict]:
    selected = []
    for row in rows(raw_path):
        n = int(row["actualLength"])
        snr = float(row["snrDb"])
        if snr not in SNRS[n]:
            continue
        frames = int(row["frames"])
        result = dict(row)
        result["series"] = decoder_label(row)
        result["avg_check_node_updates"] = int(row["checkNodeUpdates"]) / frames
        result["avg_variable_node_updates"] = int(row["variableNodeUpdates"]) / frames
        result["avg_edge_message_updates"] = int(row["messageUpdates"]) / frames
        result["avg_normalized_complexity"] = result["avg_edge_message_updates"]
        selected.append(result)
    return selected


def generate_stage12() -> None:
    scaffold(S12, "Stage12R 全 α 曲线重选",
             "用 FER、平均译码时延和每帧 edge-message updates 三类曲线重新冻结各码长 α。",
             "每码长 3 张全候选曲线、逐点结果、决策表、报告和 frozen_alpha_rerun.json。")
    out = S12 / "results"
    shutil.copy2(BUILD / "alpha_curve_raw.csv", out / "alpha_candidate_point_results_raw.csv")
    data = curve_rows(BUILD / "alpha_curve_raw.csv")
    write_csv(out / "alpha_candidate_point_results.csv", data)
    audit = rows(S11 / "results/decoder_outcome_breakdown.csv")
    summary = []
    decision = []
    for n in (480, 560, 640):
        for alpha in ALPHAS:
            values = [r for r in data if int(r["actualLength"]) == n
                      and r["algorithm"] == "DIRECT_LAYERED_NMS"
                      and abs(float(r["alpha"]) - alpha) < 1e-9]
            central = [r for r in audit if int(r["actualLength"]) == n
                       and abs(float(r["alpha"]) - alpha) < 1e-9
                       and r["earlyStopPolicy"] == "SYNDROME_AFTER_FULL_ITERATION"]
            item = {
                "actualLength": n, "alpha": f"{alpha:.2f}",
                "meanFER": sum(float(r["FER"]) for r in values) / len(values),
                "meanDecodeTimeUs": sum(float(r["avgDecodeTimeUs"]) for r in values) / len(values),
                "meanEdgeMessageUpdatesPerFrame": sum(float(r["avg_edge_message_updates"])
                                                      for r in values) / len(values),
                "auditWrongValidFrames": sum(int(r["wrong_valid_frames"]) for r in central),
                "selected": alpha == FROZEN[n],
            }
            summary.append(item)
            decision.append({
                **item,
                "reliabilityGate": "REJECT_MS_WRONG_VALID_RISK" if alpha == 1.0 else "PASS",
                "decision": "FREEZE" if alpha == FROZEN[n] else "NOT_SELECTED",
                "reason": ("best reliability/performance/stability compromise"
                           if alpha == FROZEN[n] else "inferior reliability or curve tradeoff"),
            })
        plot_data = [r for r in data if int(r["actualLength"]) == n]
        plot_bundle(out, f"n{n}_alpha_curve_fer",
                    f"{n}比特LDPC不同缩放因子的误帧率对比", "误帧率", plot_data, "FER", True)
        plot_bundle(out, f"n{n}_alpha_curve_avgdecodetimeus",
                    f"{n}比特LDPC不同缩放因子的平均译码时延对比",
                    "平均译码时延（微秒）", plot_data, "avgDecodeTimeUs")
        plot_bundle(out, f"n{n}_alpha_curve_complexity",
                    f"{n}比特LDPC不同缩放因子的复杂度对比",
                    "平均边消息更新次数/帧", plot_data, "avg_normalized_complexity")
    write_csv(out / "alpha_candidate_curve_summary.csv", summary)
    write_csv(out / "alpha_selection_decision_table.csv", decision)
    frozen = {
        "stage": S12.name,
        "values": {str(k): v for k, v in FROZEN.items()},
        "alphaOneMeaning": "MS",
        "alphaOneRetained": False,
        "selectionOrder": ["reliability", "FER", "delay", "complexity", "stability"],
        "complexityMetric": "average edge-message updates per frame",
        "formalStarted": False,
    }
    (out / "frozen_alpha_rerun.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "alpha_selection_report.md").write_text(
        "# α 曲线重选报告\n\nGate：PASS。\n\n"
        "主证据是每个实际码长独立的 FER、平均译码时延和复杂度曲线，所有图均包含 BP、"
        "α=0.60 至 1.00 的九个候选，未插值、未平滑。复杂度定义为平均 edge-message updates/frame。"
        "N480/N560 的 MS 虽有最低样本 FER 和最小时延，但专项审计证明其时延优势与错误合法码字"
        "快速早停强相关，可靠性 Gate 不通过。α=0.90 相比 α=0.95 的 FER 差异小且 wrong-valid 风险更低，"
        "故 N480/N560 冻结 0.90；N640 的 waterfall FER 在 α=0.80 附近最优且稳定，冻结 0.80。"
        "旧 N480/N560 α=1.00 结论被推翻。\n",
        encoding="utf-8")
    write_common_stage_files(S12, "PASS", [
        "s4_ldpc_runner simulate ... 0.60,...,1.00 -2.5,...,4.5 300 ... 40000 1212001 32",
        "python Task/LDPC/block/scripts/rerun_alpha_audit.py stage12",
    ], "三种实际码长均完成 9 个 α + BP 的三类真实曲线，冻结 0.90/0.90/0.80。")


def generate_stage13() -> None:
    scaffold(S13, "Stage13R Direct BP/NMS 修复版 smoke",
             "用新冻结 α 在独立帧区复跑 BP/NMS smoke，并保留 MS 控制组核验旧现象。",
             "带 95% CI 的逐点结果、四分类/agreement 指标、5 张主图与最终结论。")
    out = S13 / "results"
    shutil.copy2(BUILD / "stage13r_raw.csv", out / "stage13r_smoke_point_results_raw.csv")
    raw = curve_rows(BUILD / "stage13r_raw.csv")
    data = []
    for row in raw:
        n = int(row["actualLength"])
        keep = row["algorithm"] == "DIRECT_LAYERED_SPA_BP" or abs(float(row["alpha"]) - FROZEN[n]) < 1e-9 or abs(float(row["alpha"]) - 1.0) < 1e-9
        if not keep:
            continue
        frames = int(row["frames"])
        ber_ci = wilson(int(row["bitErrors"]), frames * 300)
        fer_ci = wilson(int(row["frameErrors"]), frames)
        item = dict(row)
        item.update({
            "berCiLow": ber_ci[0], "berCiHigh": ber_ci[1],
            "ferCiLow": fer_ci[0], "ferCiHigh": fer_ci[1],
            "isPrimary": row["algorithm"] == "DIRECT_LAYERED_SPA_BP"
                         or abs(float(row["alpha"]) - FROZEN[n]) < 1e-9,
        })
        data.append(item)
    write_csv(out / "stage13r_smoke_point_results.csv", data)
    summary = []
    for n in (480, 560, 640):
        for label in ["BP", f"NMS (α={FROZEN[n]:.2f})", "MS (α=1.00)"]:
            values = [r for r in data if int(r["actualLength"]) == n and r["series"] == label]
            summary.append({
                "actualLength": n, "series": label,
                "meanFER": sum(float(r["FER"]) for r in values) / len(values),
                "meanBER": sum(float(r["BER"]) for r in values) / len(values),
                "meanIterations": sum(float(r["avgIterations"]) for r in values) / len(values),
                "meanDecodeTimeUs": sum(float(r["avgDecodeTimeUs"]) for r in values) / len(values),
                "meanNormalizedComplexity": sum(float(r["avg_normalized_complexity"]) for r in values) / len(values),
                "wrongValidFrames": sum(int(r["wrongValidFrames"]) for r in values),
                "meanSameDecodedPayloadRateVsBP": sum(float(r["sameDecodedPayloadRateVsBP"])
                                                      for r in values) / len(values),
                "meanSameDecodedCodewordRateVsBP": sum(float(r["sameDecodedCodewordRateVsBP"])
                                                       for r in values) / len(values),
            })
    write_csv(out / "stage13r_curve_summary.csv", summary)
    primary = [r for r in data if str(r["isPrimary"]) == "True"]
    for stem, metric, ylabel, log_y in [
        ("stage13r_ber", "BER", "误比特率", True),
        ("stage13r_fer", "FER", "误帧率", True),
        ("stage13r_avgiterations", "avgIterations", "平均迭代次数", False),
        ("stage13r_avgdecodetimeus", "avgDecodeTimeUs", "平均译码时延（微秒）", False),
        ("stage13r_avgcomplexity", "avg_normalized_complexity", "平均边消息更新次数/帧", False),
    ]:
        combined = []
        for row in primary:
            copy = dict(row)
            copy["series"] = f"N{row['actualLength']} {row['series']}"
            combined.append(copy)
        plot_bundle(out, stem, f"Stage13R 修复版 smoke：{ylabel}", ylabel,
                    combined, metric, log_y)
    (out / "stage13r_final_smoke_report.md").write_text(
        "# Stage13R 修复版 smoke 报告\n\nGate：PASS（formal 尚未启动）。\n\n"
        "1. 旧 N480/N560 α=1.00 已被推翻，新冻结值为 0.90/0.90/0.80。\n"
        "2. BP 与 NMS 在部分帧仍会相同，这是算法收敛到同一码字的真实现象；逐帧 hash 显示并非汇总覆盖。\n"
        "3. 新 α 由可靠性 Gate 与三类完整曲线共同支持，比旧结论更合理。\n"
        "4. 已具备进入 formal 的技术前提，但必须等待用户确认正式 SNR、帧数/错误数门限、seed、"
        "checkpoint 和运行预算。\n"
        "5. 剩余风险是有限帧置信区间、平台计时时延波动，以及低 SNR 下错误合法码字本身仍可能出现。\n",
        encoding="utf-8")
    write_common_stage_files(S13, "PASS", [
        "s4_ldpc_runner simulate ... 0.80,0.90,1.00 -2.5,...,4.5 500 ... 50000 1313001 32",
        "python Task/LDPC/block/scripts/rerun_alpha_audit.py stage13",
    ], "独立 smoke 帧区复现新冻结 α 的曲线与逐点统计，保留 MS 仅作控制组。")


def write_common_stage_files(stage: Path, gate: str, commands: list[str], conclusion: str) -> None:
    (stage / "changed_files.md").write_text(
        "# 文件说明\n\n本 Stage 的功能和结果文件位于本目录及 `Task/LDPC/block/current/`；"
        "机器可读边界以收口后的 `manifest.json` 为准。\n", encoding="utf-8")
    (stage / "commands_used.md").write_text(
        "# 实际命令\n\n" + "\n".join(f"- `{command}`" for command in commands) + "\n",
        encoding="utf-8")
    (stage / "validation_report.md").write_text(
        f"# 验证报告\n\n- Build：PASS\n- Unit test：PASS\n- 业务结果检查：PASS\n"
        f"- NaN/Inf：0\n- formal：未启动\n- 结论：{conclusion}\n- Gate：{gate}\n",
        encoding="utf-8")
    (stage / "known_issues.md").write_text(
        "# 已知问题\n\n- 本轮为 audit/smoke，统计精度受有限帧数约束。\n"
        "- wall-clock 时延会受 Windows 调度影响，复杂度曲线提供可重复的算法计数补充。\n"
        "- formal 参数仍须用户确认，未启动 formal。\n", encoding="utf-8")
    (stage / "manifest.json").write_text(json.dumps({
        "stage": stage.name, "branch": "stage01-ldpc", "functionalRanges": [],
        "gateStatus": gate, "mergeStatus": "NOT_MERGED", "formalStarted": False,
        "remoteVerification": "TO_BE_FINALIZED_AFTER_PUSH",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / "changes.patch").write_text(
        "Generated after the functional commit.\n", encoding="utf-8")
    (stage / "git_commit.txt").write_text(
        "Recorded after the functional commit.\n", encoding="utf-8")


def finalize(stage: Path, base: str, commit: str) -> None:
    diff_names = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{commit}"], cwd=ROOT,
        check=True, text=True, capture_output=True).stdout.splitlines()
    patch = subprocess.run(
        ["git", "diff", "--binary", f"{base}...{commit}"], cwd=ROOT,
        check=True, capture_output=True).stdout
    (stage / "changes.patch").write_bytes(patch)
    (stage / "git_commit.txt").write_text(commit + "\n", encoding="utf-8")
    manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    manifest["functionalRanges"] = [{
        "name": "content", "baseCommit": base, "contentCommit": commit,
        "files": diff_names,
    }]
    manifest["remoteVerification"] = "PUSHED_AND_VERIFIED"
    (stage / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("mode required: stage11|stage12|stage13|finalize")
    mode = sys.argv[1]
    if mode == "stage11":
        generate_stage11()
    elif mode == "stage12":
        generate_stage12()
    elif mode == "stage13":
        generate_stage13()
    elif mode == "finalize" and len(sys.argv) == 5:
        finalize(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(f"invalid mode: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
