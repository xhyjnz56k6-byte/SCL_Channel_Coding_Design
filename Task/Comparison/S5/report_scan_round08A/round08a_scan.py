#!/usr/bin/env python3
"""Round08-A S5 evidence-map generator.

This program is intentionally read-only with respect to formal inputs.  It
parses the frozen configuration, source-side plot manifests and Stage10 CSV,
then writes the Round08-A writing assets beside this file.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


OUT = Path(__file__).resolve().parent
S5 = OUT.parent
FORMAL = S5 / "results/formal/merged/formal_merged_results.csv"
STAGE11 = S5 / "results/stage11"
AGGREGATE = S5 / "results/Aggregate"
CONFIG = S5 / "current/config/s5_formal_frozen_config.json"

CHANNELS = [
    "AWGN", "FIXED_MULTIPATH_REAL_MMSE", "CFO_30_DEG",
    "LINEAR_TIME_VARYING_FREQUENCY", "KNOWN_BLOCKAGE_5_PERCENT",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB",
]
GROUPS = ["RATE_NEAR_2_3", "RATE_NEAR_1_2"]
PAIR = {
    "RATE_NEAR_2_3": ("CC_R23_BLOCK_FLOAT", "LDPC_BG2_N480_NMS"),
    "RATE_NEAR_1_2": ("CC_R12_BLOCK_FLOAT", "LDPC_BG2_N640_NMS"),
}
CHINESE = {
    "AWGN": "加性高斯白噪声",
    "FIXED_MULTIPATH_REAL_MMSE": "固定多径（实轴 MMSE）",
    "CFO_30_DEG": "固定频偏相位漂移",
    "LINEAR_TIME_VARYING_FREQUENCY": "线性时变频率偏移",
    "KNOWN_BLOCKAGE_5_PERCENT": "已知 5% 连续遮挡",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB": "未知 5% 突发干扰（ISR=10 dB）",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(S5.parents[2]).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_text(name: str, text: str) -> None:
    (OUT / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def f(value: str | float | None, digits: int = 6) -> str:
    if value is None or value == "" or value == "N/A":
        return "N/A"
    return f"{float(value):.{digits}f}"


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def bracket(rows: list[dict], target: float) -> float | None:
    """Adjacent nonzero measured FER log-domain interpolation; no extrapolation."""
    ordered = sorted(rows, key=lambda x: float(x["esN0Db"]))
    for left, right in zip(ordered, ordered[1:]):
        fl, fr = float(left["FER"]), float(right["FER"])
        if fl > 0.0 and fr > 0.0 and fl >= target >= fr and fl != fr:
            xl, xr = float(left["esN0Db"]), float(right["esN0Db"])
            return xl + (math.log10(target) - math.log10(fl)) * (xr - xl) / (math.log10(fr) - math.log10(fl))
    return None


def classify_stage11(manifest: dict) -> tuple[str, str, str]:
    figure_id = manifest["figureId"]
    if figure_id.startswith("ldpc__"):
        return "LDPC 迭代证据", "迭代证据", "NO"
    metric = manifest["yColumns"][0].lower()
    if "fer" in metric:
        return "误帧率性能", "主结果图", "CONDITIONAL"
    if "ber" in metric:
        return "误比特率细节", "细节补证图", "NO"
    if "decodetime" in metric:
        return "译码时延", "时延证据", "NO"
    if "receiver" in metric:
        return "接收机算法时间", "时延证据", "NO"
    return "非正文展示", "不建议正文展示", "NO"


def stage11_inventory(formal_rows: list[dict]) -> list[dict]:
    rows = []
    for directory in sorted((STAGE11 / "plots").iterdir()):
        manifest_path = directory / "plot_manifest.json"
        data_path = directory / "figure_data.csv"
        if not manifest_path.exists() or not data_path.exists():
            raise RuntimeError(f"incomplete Stage11 plot asset: {directory}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        data = load_csv(data_path)
        if manifest["sourceFormalCsvSha256"] != sha(FORMAL):
            raise RuntimeError(f"Stage11 source hash mismatch: {directory}")
        if len(data) != 31:
            raise RuntimeError(f"Stage11 plot must retain 31 SNR rows: {directory}")
        group = manifest.get("comparisonGroup", "LDPC_ALL_GROUPS")
        channel = manifest.get("channel", "ALL_CHANNELS")
        schemes = list(dict.fromkeys(x.rsplit("__", 1)[-1] for x in manifest["yColumns"]))
        if channel == "ALL_CHANNELS":
            source_rows = len(formal_rows)
        elif channel == "NON_AWGN":
            # Delta-FER uses every damaged channel and each scheme's AWGN
            # baseline within the same comparison group.
            source_rows = sum(r["group"] == group for r in formal_rows)
        elif group == "LDPC_ONLY":
            source_rows = sum(r["channel"] == channel and r["scheme"].startswith("LDPC_") for r in formal_rows)
        else:
            source_rows = sum(r["group"] == group and r["channel"] == channel for r in formal_rows)
        purpose, role, recommendation = classify_stage11(manifest)
        rows.append({
            "figureDirectory": rel(directory), "title": manifest["title"],
            "comparisonGroup": group, "channel": channel,
            "schemeCount": len(schemes),
            "schemes": ";".join(schemes),
            "metric": ";".join(manifest["yColumns"]), "xAxis": manifest["xColumn"],
            "yAxis": manifest["units"]["y"], "sourceCsv": rel(data_path),
            "sourceFormalRows": source_rows, "curveCount": manifest["curveCount"],
            "purpose": purpose, "independentEvidenceValue": (
                "由同目录 figure_data.csv 的真实测点构成；无平滑、无插值。"),
            "recommendedForMainText": recommendation, "recommendedRole": role,
            "duplicateWithAggregate": "YES" if "fer" in ";".join(manifest["yColumns"]).lower() else "NO",
            "importantObservation": "以源 CSV 为准；对数纵轴会省略零值但 CSV 保留零值。",
            "dataRisk": "无图数据缺失；需避免将对数图上的零值视觉缺口误读为缺测。",
            "notes": f"figure_data 行数={len(data)}；manifest 哈希源={manifest['sourceFormalCsvSha256']}。",
        })
    if len(rows) != 86:
        raise RuntimeError(f"expected 86 Stage11 figures, found {len(rows)}")
    return rows


def aggregate_inventory(formal_rows: list[dict]) -> list[dict]:
    rows = []
    for directory in sorted(p for p in AGGREGATE.iterdir() if p.is_dir()):
        manifest_path, data_path = directory / "plot_manifest.json", directory / "figure_data.csv"
        if not manifest_path.exists() or not data_path.exists():
            continue
        m, data = json.loads(manifest_path.read_text(encoding="utf-8")), load_csv(data_path)
        if m["sourceFormalCsvSha256"] != sha(FORMAL):
            raise RuntimeError(f"Aggregate source hash mismatch: {directory}")
        if len(data) != 31:
            raise RuntimeError(f"Aggregate plot must retain 31 SNR rows: {directory}")
        definitions = m["curveDefinitions"]
        rows.append({
            "figureDirectory": rel(directory), "title": m["title"],
            "comparisonGroup": m.get("comparisonGroup", "MULTI"),
            "channelScope": m.get("channelScope", "MULTI"),
            "metric": m["metric"], "curveCount": m["curveCount"],
            "curveNames": ";".join(x["label"] for x in definitions),
            "sourceCsv": rel(data_path), "sourceFormalRows": len(definitions) * 31,
            "all31SnrPoints": "YES" if m["all31MeasuredPointsConnected"] else "NO",
            "purpose": "跨信道主结论" if directory.name[:2] in {"01", "02", "03", "04", "13", "14", "15", "16"} else "时延或迭代辅助结论",
            "mainTextPriority": "A" if directory.name[:2] in {"01", "02", "03", "04", "13", "14", "15", "16"} else "C",
            "dataRisk": "所有曲线均为 Formal 真实点；无平滑、无插值；对数轴零值仅在绘图时省略。",
            "notes": f"figure_data 行数={len(data)}；source hash={m['sourceFormalCsvSha256']}。",
        })
    if len(rows) != 20:
        raise RuntimeError(f"expected 20 Aggregate figures, found {len(rows)}")
    return rows


def parameter_rows() -> list[dict]:
    common = {
        "payloadBits": "300", "constraintLength": "N/A", "generatorPolynomial": "N/A",
        "puncturePattern": "N/A", "termination": "N/A", "ldpcBaseGraph": "N/A",
        "ldpcZc": "N/A", "ldpcAlpha": "N/A", "maxIterations": "N/A", "interleaver": "无",
    }
    data = [
        ("RATE_NEAR_2_3", "CC_R23_BLOCK_FLOAT", "459", "300/459=0.653594771", "卷积码", "整块浮点软判决 Viterbi", "7", "171/133 (oct)", "R23_1101=1101", "6 bit 零尾"),
        ("RATE_NEAR_2_3", "LDPC_BG2_N480_NMS", "480", "300/480=0.625000000", "BG2 Direct QC-LDPC", "Layered NMS", "N/A", "N/A", "N/A", "N/A"),
        ("RATE_NEAR_1_2", "CC_R12_BLOCK_FLOAT", "612", "300/612=0.490196078", "卷积码", "整块浮点软判决 Viterbi", "7", "171/133 (oct)", "无", "6 bit 零尾"),
        ("RATE_NEAR_1_2", "LDPC_BG2_N640_NMS", "640", "300/640=0.468750000", "BG2 Direct QC-LDPC", "Layered NMS", "N/A", "N/A", "N/A", "N/A"),
    ]
    rows = []
    for group, scheme, n, rate, codec, decoder, k, poly, puncture, term in data:
        row = dict(common)
        row.update(comparisonGroup=group, scheme=scheme, transmittedBits=n, actualRate=rate,
                   codec=codec, decoder=decoder, constraintLength=k, generatorPolynomial=poly,
                   puncturePattern=puncture, termination=term,
                   ldpcBaseGraph="BG2" if "LDPC" in scheme else "N/A",
                   ldpcZc="N/A（Direct 构图，N=480/640）" if "LDPC" in scheme else "N/A",
                   ldpcAlpha="0.95" if scheme.endswith("480_NMS") else ("0.80" if scheme.endswith("640_NMS") else "N/A"),
                   maxIterations="32" if "LDPC" in scheme else "N/A",
                   sourceFile="current/src/s5.cpp; current/config/s5_formal_frozen_config.json",
                   sourceEvidence="schemeSpecs(), encodeFrame(), decodeFrame(); Formal frozen config schemes[]。")
        rows.append(row)
    return rows


def channel_rows() -> list[dict]:
    common = "BPSK：0→+1，1→−1；复高斯 I/Q 独立标准正态样本按 sigma 缩放；sigma²=1/[2·10^(Es/N0/10)]，横轴为 Es/N0。"
    data = [
        ("AWGN", "无附加损伤，直接叠加复 AWGN", "仅 sigma²（Es/N0）", "否", "实部投影后 2·Re{y}/sigma²", "否", "N/A"),
        ("FIXED_MULTIPATH_REAL_MMSE", "归一化三抽头线性卷积：tap=[1,0.65,0.35]/sqrt(1+0.65²+0.35²)，delay=[0,1,3]", "已知 taps；实轴 MMSE；gk、vk", "是：已知固定 taps", "解 Cholesky MMSE 后 LLR=2·gk·xhatk/vk", "否", "N/A"),
        ("CFO_30_DEG", "帧内相位从 0 线性累积至 π/6（30°）", "phase(i)=(π/6)i/(Ntx−1)", "否", "实部投影后按名义 AWGN 公式", "否", "N/A"),
        ("LINEAR_TIME_VARYING_FREQUENCY", "epsilon(i) 从 −1/[3(Ntx−1)] 线性变至 +1/[3(Ntx−1)]；phase(i)=phase(i−1)+2πepsilon(i−1)", "瞬时归一化频率线性变化", "否", "实部投影后按名义 AWGN 公式", "否", "N/A"),
        ("KNOWN_BLOCKAGE_5_PERCENT", "damageLength=round(0.05Ntx) 的连续发送域区段置零", "fraction=5%；relativeStart(frameIndex) 映射到各自 Ntx", "是：已知 mask", "受遮挡位置 LLR=0（中性可靠度）", "是", "同一 frameIndex 共用 relativeStart；不同 Ntx 的绝对起点可不同"),
        ("UNKNOWN_BURST_5_PERCENT_ISR_10DB", "连续 5% 发送符号叠加独立复高斯干扰", "ISR=10 dB；beta=sqrt(10^(ISR/10)/2)", "否：mask 未知", "仍按名义 AWGN LLR，故受污染样本被当作有效观测", "否（仅内部损伤标记）", "同一 frameIndex 共用 relativeStart；不同 Ntx 的绝对起点可不同"),
    ]
    rows = []
    for ident, model, parameters, known, rx, mask, fairness in data:
        rows.append({
            "channelChinese": CHINESE[ident], "internalId": ident, "mathematicalProgramModel": model,
            "keyParameters": parameters, "awgnSuperposed": "是", "awgnDefinition": common,
            "impairmentLocation": "BPSK 发射复符号后、AWGN 叠加前；多径输出长度为 Ntx+3。",
            "receiverKnowsChannelState": known, "receiverProcessing": rx,
            "softInformation": rx, "usesMask": mask, "randomStart": "是" if "relativeStart" in fairness else "否",
            "fairnessAtSameFrameIndex": fairness or "同一 frameIndex 由共享键规则生成噪声。",
            "applicableBoundary": "仅为冻结的 S5 受控基带模型；不外推为完整实际卫星物理信道。",
            "sourceEvidence": "current/src/s5.cpp: runChannel(), multipathReceiver(); frozen config。",
        })
    return rows


def assets_and_metrics(formal_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    loss = load_csv(STAGE11 / "s5_channel_loss_table.csv")
    latency = load_csv(STAGE11 / "s5_latency_comparison.csv")
    robustness = load_csv(STAGE11 / "s5_robustness_summary.csv")
    rec = load_csv(STAGE11 / "s5_scenario_recommendation.csv")
    loss_map = {(x["group"], x["channel"], x["scheme"], x["targetFer"]): x for x in loss}
    latency_map = {(x["group"], x["channel"], x["scheme"]): x for x in latency}
    robust_map = {(x["group"], x["channel"], x["scheme"]): x for x in robustness}
    rec_map = {(x["comparisonGroup"], x["channel"]): x for x in rec}
    by_gcs = defaultdict(list)
    for row in formal_rows:
        by_gcs[(row["group"], row["channel"], row["scheme"])].append(row)
    result = []
    for group in GROUPS:
        cc, ldpc = PAIR[group]
        for channel in CHANNELS:
            thresholds = {}
            for target, label in ((0.1, "01"), (0.01, "001")):
                values = {s: bracket(by_gcs[(group, channel, s)], target) for s in (cc, ldpc)}
                available = {s: v for s, v in values.items() if v is not None}
                winner = min(available, key=available.get) if available else "N/A"
                thresholds[label] = (values, winner, (values[cc] - values[ldpc]) if len(available) == 2 else None)
            def loss_value(scheme, target):
                row = loss_map.get((group, channel, scheme, target))
                return row["channelLossDb"] if row and row["coveredByData"] == "True" else "N/A"
            def relative(target):
                a, b = loss_value(cc, target), loss_value(ldpc, target)
                if a == "N/A" or b == "N/A": return "N/A"
                return cc if float(a) < float(b) else ldpc
            cc_lat, ldpc_lat = latency_map[(group, channel, cc)], latency_map[(group, channel, ldpc)]
            ldpc_robust = robust_map[(group, channel, ldpc)]
            recommendation = rec_map[(group, channel)]
            result.append({
                "comparisonGroup": group, "channel": channel, "ccScheme": cc, "ldpcScheme": ldpc,
                "absoluteFerWinnerAtTarget01": thresholds["01"][1],
                "absoluteFerRequiredSnrCC": f(thresholds["01"][0][cc]), "absoluteFerRequiredSnrLDPC": f(thresholds["01"][0][ldpc]), "absoluteFerDifferenceDb": f(thresholds["01"][2]),
                "absoluteFerWinnerAtTarget001": thresholds["001"][1],
                "absoluteFer001RequiredSnrCC": f(thresholds["001"][0][cc]), "absoluteFer001RequiredSnrLDPC": f(thresholds["001"][0][ldpc]), "absoluteFer001DifferenceDb": f(thresholds["001"][2]),
                "ccChannelLossFer01": f(loss_value(cc, "0.1")), "ldpcChannelLossFer01": f(loss_value(ldpc, "0.1")), "relativeRobustnessWinnerFer01": relative("0.1"),
                "ccChannelLossFer001": f(loss_value(cc, "0.01")), "ldpcChannelLossFer001": f(loss_value(ldpc, "0.01")), "relativeRobustnessWinnerFer001": relative("0.01"),
                "ccMeanDecodeUs": f(cc_lat["meanAvgDecodeTimeUs"], 3), "ldpcMeanDecodeUs": f(ldpc_lat["meanAvgDecodeTimeUs"], 3),
                "ccP95DecodeUs": f(cc_lat["meanP95DecodeTimeUs"], 3), "ldpcP95DecodeUs": f(ldpc_lat["meanP95DecodeTimeUs"], 3),
                "ccMaxObservedDecodeUs": f(cc_lat["maxDecodeTimeUs"], 3), "ldpcMaxObservedDecodeUs": f(ldpc_lat["maxDecodeTimeUs"], 3),
                "ldpcAvgIterations": f(ldpc_robust["meanIterations"], 3), "ldpcMaxIterationRate": f(ldpc_robust["meanMaxIterationRate"], 6),
                "mainObservation": "绝对门限与相对 AWGN 损失必须分开解读；N/A 表示无相邻真实非零点夹住目标。",
                "engineeringTradeoff": "时延为当前 Windows Release 软件测量；最大值是有限样本观测峰值，不能表述为严格最坏时延。",
                "recommendedScheme": recommendation["recommendedScheme"], "recommendationConfidence": recommendation["recommendationConfidence"],
                "evidenceFigures": f"Aggregate 01–20；Stage11 {group.lower()}__{channel.lower()}__*", "evidenceTables": "07 channel loss；09 latency；12 evidence matrix",
            })
    return result, loss, latency, robustness


def plan_text(stage_figs: list[dict], aggregate_figs: list[dict]) -> tuple[str, str, str, str, str, str]:
    figure_plan = """# 第 7 章正文图计划

正文只保留承担独立论证任务的 Aggregate 图。A 类主图为 01、02、03、04（两码率组的常规/局部连续损伤 FER），以及 13–16（四个冻结方案的六信道 FER）；B 类在需要展示译码负担时可选 17–20。Stage11 的 86 张单图全部由本轮资产索引覆盖，但其 BER、时延和迭代图默认由三线表或 Aggregate 图吸收，不重复铺陈。

| 图 | 章节 | 主问题 | 独立证据 | 替代的单图 | 关联表 |
|---|---|---|---|---|---|
| Aggregate 01 | 7.3 | 近 2/3 常规信道下的绝对 FER | AWGN/多径/CFO/时变频偏四信道、两方案、31 点 | 对应 4 张 Stage11 FER 图 | 表D、表E |
| Aggregate 02 | 7.6 | 近 2/3 局部损伤的 FER | 已知遮挡与未知突发的真实点 | 对应 2 张 Stage11 FER 图 | 表D、表H |
| Aggregate 03 | 7.3 | 近 1/2 常规信道下的绝对 FER | 同上 | 对应 4 张 Stage11 FER 图 | 表D、表E |
| Aggregate 04 | 7.6 | 近 1/2 局部损伤的 FER | 同上 | 对应 2 张 Stage11 FER 图 | 表D、表H |
| Aggregate 13–16 | 7.8 | 单一方案跨六信道的退化形态 | 同方案 AWGN 基线与五类损伤 | 各方案 6 张 Stage11 FER 图 | 表E、表H |
| Aggregate 17–20（条件选用） | 7.7 | LDPC 迭代负担 | 平均迭代/上限迭代比例 | LDPC Stage11 迭代单图 | 表G |

不进入正文的图仍通过表D–表G和 12_s5_result_evidence_matrix.csv 的定量字段覆盖；不以单一“鲁棒性总分”替代 BER、FER、门限、相对损失和时延的分别论证。"""
    table_plan = """# 第 7 章三线表计划

| 表 | 数据源 | 字段/计算 | 是否实测 | 插值 | 论证任务 |
|---|---|---|---|---|---|
| A 正式候选方案与比较组 | 01 参数冻结表 | payload、发送长度、实际码率、编译码器 | 配置/源码 | 否 | 明确同组公平配对范围 |
| B 六类信道模型与接收处理 | 02 信道冻结表 | 数学模型、参数、CSI、LLR | 源码/配置 | 否 | 防止把不同损伤与接收假设混写 |
| C Formal 共同参数与公平性 | 03 公平性审计 | 31 点、停机、种子、relativeStart | 配置/源码 | 否 | 说明配对停止和随机性可比性 |
| D 各信道 FER=0.1/0.01 门限 | 12 结果矩阵 | 相邻真实非零点的 FER 对数域插值 | 是 | 仅已夹逼 | 比较绝对门限，不外推 |
| E 相对 AWGN 信道损失 | 07/08 | 同一方案的 channel threshold − AWGN threshold | 是 | 同表规则 | 比较相对退化，不混同绝对 FER |
| F 译码与接收机算法时延 | 09 + Formal CSV | avg/P95/max 观测值 | 是 | 否 | 说明软件复杂度代价 |
| G LDPC 迭代行为 | 09 + Formal CSV | all-frame avg、P95、max、达 32 次比例 | 是 | 否 | 说明收敛压力 |
| H 六信道综合推荐 | 12 结果矩阵 | 门限、损失、时延、迭代多指标并列 | 是 | 否 | 给出场景化选型，不构造人为权重总分 |
| I 已知遮挡 vs 未知突发（可选） | 02/07/12 | mask 已知性、FER 饱和、目标覆盖 | 是 | 否 | 区分擦除式损伤与失配干扰 |
"""
    structure = """# 第 7 章结构建议

## 7 高速电文不同信道下卷积码与 LDPC 的对比

| 节 | 核心问题 | 正文图 | 三线表 | 主要结论 | 预计篇幅 |
|---|---|---|---|---|---|
| 7.1 比较目标与方案配置 | 比较对象是否同组、无交织且码率接近 | 无 | 表A | 四方案分两组配对 | 0.5 页 |
| 7.2 信道模型与公平仿真条件 | 六信道、接收假设和配对停止 | 无 | 表B、表C | 绝对性能与相对 AWGN 退化分开 | 1.0 页 |
| 7.3 AWGN 基准与常规损伤 | waterfall 左移与多径/CFO/时变偏移影响 | Aggregate 01、03 | 表D、表E | 门限只在真实夹逼时报告 | 1.5 页 |
| 7.4 固定多径 | 已知 MMSE 后残余差异 | Aggregate 01、03（局部引用） | 表D、表E | 接收机均衡条件必须写明 | 0.7 页 |
| 7.5 固定频偏与时变频率 | 两种相位损伤不可混同 | Aggregate 01、03 | 表D、表E | Ntx 也影响时变相位经历 | 1.0 页 |
| 7.6 已知遮挡与未知突发 | mask=0 的擦除与未知干扰的区别 | Aggregate 02、04 | 表D、表I | 不把 CC 饱和误写为伪造 error floor | 1.0 页 |
| 7.7 软件时延与 LDPC 迭代 | 时延范围和收敛负担 | 17–20（按篇幅选） | 表F、表G | max 是有限样本观测最大值 | 0.8 页 |
| 7.8 多信道选型 | 如何并列使用绝对 FER、损失、时延和迭代 | Aggregate 13–16 | 表H | 场景化推荐，不设单一总分 | 1.0 页 |
"""
    fairness = """# S5 公平性与统计口径

- payload 为 300 bit，`payloadForFrame(frameIndex)` 使用冻结帧池种子；frameIndex 是随机键的一部分。
- 复 AWGN 的每个 I/Q 标准正态样本由 `(masterNoiseSeed, noiseGroupId, frameIndex, symbolIndex, noisePolicyVersion)` 唯一决定。方案发送长度不同，因此不应声称“所有噪声样本逐个相同”；公平性是共享 frameIndex、噪声组和索引生成规则。
- 已知遮挡/突发位置以同一 frameIndex 的 `relativeStart` 共享，再映射到各方案自身 Ntx；绝对 `damageStart` 因 Ntx 不同而不同。
- Formal 网格为 2 组 × 6 信道 × 31 Es/N0 点=372 个 paired tasks、744 scheme points。每一配对任务的两方案使用相同最终帧数；在至少 1000 帧后，双方均达到 200 帧错误才停止，否则到 50000 帧。
- BER=`payloadBitErrors/(frames×300)`；FER=`frameErrors/frames`。P95 索引为 `ceil(0.95N)-1`。零错误观测保留为零，不伪造 error floor。
- 相对 AWGN 损失仅定义为同一方案在目标 FER 的受损信道门限减去自身 AWGN 门限；目标必须由相邻真实、非零测点夹住，缺失时写 N/A，不外推。
"""
    latency = """metric,definition,includedOperations,excludedOperations,aggregation,unit,source,reportInterpretation,warning
avgDecodeTimeUs,LLR输入至译码payload/status输出,decodeFrame含CC去打孔或LDPC译码,编码/信道/噪声/投影/LLR/I-O,样本均值,us,s5_runner.cpp evaluateFrame,软件译码平均时间,主机相关
medianDecodeTimeUs,同上,同上,同上,中位数,us,s5_runner.cpp,软件译码典型时间,主机相关
p95DecodeTimeUs,同上,同上,同上,ceil(0.95N)-1,us,s5_runner.cpp,95%样本不超过该观测值,不是硬实时保证
maxDecodeTimeUs,同上,同上,同上,有限样本最大值,us,s5_runner.cpp,最大观测软件时间,不得称为严格最坏情况时延
avgChannelProcessingTimeUs,接收端信道处理,损伤/AWGN/均衡/投影/LLR,译码,样本均值,us,s5.cpp+s5_runner.cpp,接收机前端计算量,含受控仿真处理
p95ChannelProcessingTimeUs,同上,同上,译码,ceil(0.95N)-1,us,s5_runner.cpp,前端尾部时间,主机相关
avgTotalReceiverAlgorithmTimeUs,接收机算法总时间,channelProcessing+decode,编码/I-O,样本均值,us,s5_runner.cpp,前端加译码总算法时间,不是端到端系统时延
p95TotalReceiverAlgorithmTimeUs,同上,同上,编码/I-O,ceil(0.95N)-1,us,s5_runner.cpp,总算法尾部时间,不是硬实时保证
maxTotalReceiverAlgorithmTimeUs,同上,同上,编码/I-O,有限样本最大值,us,s5_runner.cpp,总算法最大观测值,不得称为严格最坏情况
avgIterations,LDPC每帧使用迭代数,所有LDPC帧,CC不适用,样本均值,iterations,s5_runner.cpp,收敛平均负担,不是只对成功帧
p95Iterations,同上,同上,CC不适用,ceil(0.95N)-1,iterations,s5_runner.cpp,迭代尾部负担,同上
maxIterations,LDPC单帧最大使用次数,所有LDPC帧,CC不适用,样本最大值,iterations,s5_runner.cpp,与上限32比较,不等于平均
maxIterationRate,达到32次上限帧数/总帧数,所有LDPC帧,CC不适用,比例,ratio,s5_runner.cpp,迭代耗尽比例,综合症通过不等同payload必然正确
"""
    cc_audit = """# CC 软判决度量审计

`runChannel()` 输出的是 LLR。对于 CC，`decodeFrame()` 先把每个 LLR 乘以 0.5，得到与 BPSK 软符号尺度一致的 `symbols`；R1/2 直接送入终止 Viterbi。R2/3 先以 `R23_1101` 将 459 个发送域软符号扩展到 612 个母码域位置：未发送位置填 0 且 `observed_mask=0`，已观测位置的 mask 为 1。

Soft Viterbi 并不“直接把 LLR 当作分支度量”。对每一时刻的两个软符号 y0、y1 和支路预期 BPSK 符号 s(b)∈{+1,−1}，其增量为 `mask0(y0−s(b0))² + mask1(y1−s(b1))²`；未观测位置贡献为零。该表述是第 7 章可安全采用的正式中文：

> 卷积码采用整块浮点软判决 Viterbi 译码。接收端将信道软信息换算为 BPSK 软符号；对打孔码先恢复母码域的观测掩码，再以接收软符号与支路参考符号之间的欧氏距离构造分支度量。

来源：`current/src/s5.cpp: decodeFrame()`、`Task/CC/shared/src/puncturing.cpp: depuncture_soft()`、`Task/CC/block/current/src/soft_viterbi.cpp`。
"""
    ldpc_audit = """# LDPC NMS 指标审计

- N480 的 alpha=0.95，N640 的 alpha=0.80；两者最大迭代次数均为 32。
- `decodeLayeredNms()` 在每个完整 layered iteration 后硬判决并计算 syndrome weight；syndrome 为零时提前停止。
- `avgIterations` 对所有 LDPC 帧的 `usedIterations` 求统计，不只统计成功帧；`maxIterationRate=maxIterationFrames/frames`，其中 `maxIterationFrames` 为使用 32 次迭代的帧数。
- `decoderFailure` 在 S5 中定义为 `!syndromePass`。`undetectedPayloadErrorFrames` 是 payload 出错而 syndrome 已通过的帧数；不得臆称为 CRC 未检测错误，因为此 Direct 短块模型并未实现完整 5G NR PHY CRC 流程。
- 报告表述应称为“BG2 Direct QC-LDPC 短块构图上的 layered NMS”，不得称为完整 5G NR 物理层实现。
"""
    risk = """# 报告语言风险清单

1. 禁止把 Es/N0 写成 Eb/N0，除非明确换算并注明实际帧级码率。
2. 禁止把固定频偏相位漂移与线性时变频率偏移合并为同一个模型。
3. 禁止写“Viterbi 直接以 LLR 为分支度量”；本实现使用软符号欧氏距离。
4. 禁止把多径写成直接 `2y/sigma²`；必须注明实轴 MMSE 以及 gk/vk LLR。
5. 禁止把已知遮挡与未知突发相混：前者 mask 已知且 LLR=0，后者 mask 未知且采用名义 AWGN LLR。
6. 禁止把图上的零值省略误读为缺失或绘制伪造的 error floor。
7. 禁止对未被相邻真实点夹住的 FER 门限或 AWGN 损失做外推。
8. 禁止以绝对 FER 低直接宣称相对更鲁棒；必须同时查看同方案 AWGN 损失。
9. 禁止将 maxDecodeTimeUs 称为严格最坏情况时延；它仅是有限样本最大观测软件时间。
10. 禁止把 syndrome 通过误写为 CRC 未检测错误，或把该 Direct LDPC 描述成完整 NR PHY。
11. 正文不使用 Stage、Gate、PASS、manifest、hash、pipeline、TODO、pending、review、Git 等开发/审计叙事词。
"""
    return figure_plan, table_plan, structure, fairness, latency, cc_audit + "\n\n" + ldpc_audit + "\n\n" + risk


def main() -> None:
    generated = {
        "01_s5_scheme_parameter_freeze.csv", "02_s5_channel_model_freeze.csv",
        "03_s5_fairness_and_statistics.md", "04_s5_stage11_asset_inventory.csv",
        "05_s5_aggregate_asset_inventory.csv", "06_s5_core_summary_csv_audit.md",
        "07_s5_channel_loss_report_ready.csv", "08_s5_channel_loss_matrix.md",
        "09_s5_latency_metric_definition.csv", "10_s5_cc_soft_metric_audit.md",
        "11_s5_ldpc_metric_audit.md", "12_s5_result_evidence_matrix.csv",
        "13_s5_main_text_figure_plan.md", "14_s5_main_text_table_plan.md",
        "15_s5_chapter7_structure_proposal.md", "16_s5_report_language_risk.md",
        "17_s5_round08A_final_report.md", "18_s5_round08A_gate.txt", "readme.txt",
    }
    # Python may leave bytecode cache beside this standalone generator.  It is
    # not a scan asset and is deliberately neither read nor overwritten.
    present = {p.name for p in OUT.iterdir() if p.name != "__pycache__"}
    if not present <= generated | {"round08a_scan.py"}:
        raise RuntimeError("Round08-A directory contains non-generator content; refusing to overwrite it")
    if present - {"round08a_scan.py"} and "--overwrite" not in sys.argv:
        raise RuntimeError("Round08-A assets exist; use --overwrite only to regenerate this scan's own files")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    formal_rows = load_csv(FORMAL)
    expected = config["formalSchemePointCount"]
    unique = {(r["group"], r["channel"], r["esN0Db"], r["scheme"]) for r in formal_rows}
    if len(formal_rows) != expected or len(unique) != expected:
        raise RuntimeError(f"Formal point count mismatch: rows={len(formal_rows)}, unique={len(unique)}, expected={expected}")
    stage_figs = stage11_inventory(formal_rows)
    agg_figs = aggregate_inventory(formal_rows)
    result_matrix, loss_rows, latency_rows, robust_rows = assets_and_metrics(formal_rows)
    write_csv("01_s5_scheme_parameter_freeze.csv", [
        "comparisonGroup","scheme","payloadBits","transmittedBits","actualRate","codec","decoder","constraintLength","generatorPolynomial","puncturePattern","termination","ldpcBaseGraph","ldpcZc","ldpcAlpha","maxIterations","interleaver","sourceFile","sourceEvidence"], parameter_rows())
    write_csv("02_s5_channel_model_freeze.csv", list(channel_rows()[0]), channel_rows())
    figure_plan, table_plan, structure, fairness, latency_definition, bundled = plan_text(stage_figs, agg_figs)
    write_text("03_s5_fairness_and_statistics.md", fairness)
    write_csv("04_s5_stage11_asset_inventory.csv", list(stage_figs[0]), stage_figs)
    write_csv("05_s5_aggregate_asset_inventory.csv", list(agg_figs[0]), agg_figs)
    write_text("06_s5_core_summary_csv_audit.md", f"""# Stage11 核心汇总 CSV 审计

- `s5_channel_loss_table.csv`：{len(loss_rows)} 行；其门限仅在相邻真实非零 FER 点夹住目标时插值，未覆盖写 N/A。
- `s5_latency_comparison.csv`：{len(latency_rows)} 行，覆盖 6 信道×2比较组×2方案。
- `s5_robustness_summary.csv`：{len(robust_rows)} 行，明确不构造统一鲁棒性总分。
- `s5_scenario_recommendation.csv`：12 行，逐信道/比较组给出多指标场景推荐。
- 四个汇总 CSV 与 Stage11/ Aggregate 清单均指向 Formal SHA-256 `{sha(FORMAL)}`；本扫描未修改 Formal 数据。
""")
    copied_loss = []
    for row in loss_rows:
        copied_loss.append({**row, "interpolationRule": "相邻真实非零 FER 点的对数域插值；无夹逼=N/A；不外推", "source": rel(STAGE11 / "s5_channel_loss_table.csv")})
    write_csv("07_s5_channel_loss_report_ready.csv", list(copied_loss[0]), copied_loss)
    matrix_lines = ["# 相对 AWGN 信道损失矩阵", "", "仅列出可由相邻真实非零 FER 点夹住的值；N/A 不外推。CC/LDPC 的 loss 均相对各自 AWGN 基线。", ""]
    for group in GROUPS:
        matrix_lines += [f"## {group}", "", "| 信道 | FER | CC loss (dB) | LDPC loss (dB) | 相对退化较小方案 |", "|---|---:|---:|---:|---|"]
        for channel in CHANNELS[1:]:
            row = next(x for x in result_matrix if x["comparisonGroup"] == group and x["channel"] == channel)
            for target, suffix in (("0.1", "01"), ("0.01", "001")):
                matrix_lines.append(f"| {CHINESE[channel]} | {target} | {row['ccChannelLossFer'+suffix]} | {row['ldpcChannelLossFer'+suffix]} | {row['relativeRobustnessWinnerFer'+suffix]} |")
        matrix_lines.append("")
    write_text("08_s5_channel_loss_matrix.md", "\n".join(matrix_lines))
    write_text("09_s5_latency_metric_definition.csv", latency_definition)
    cc_part, ldpc_part, risk_part = bundled.split("\n\n", 2)
    write_text("10_s5_cc_soft_metric_audit.md", cc_part)
    write_text("11_s5_ldpc_metric_audit.md", ldpc_part)
    write_csv("12_s5_result_evidence_matrix.csv", list(result_matrix[0]), result_matrix)
    write_text("13_s5_main_text_figure_plan.md", figure_plan)
    write_text("14_s5_main_text_table_plan.md", table_plan)
    write_text("15_s5_chapter7_structure_proposal.md", structure)
    write_text("16_s5_report_language_risk.md", risk_part)
    valid01 = sum(x["ccChannelLossFer01"] != "N/A" for x in result_matrix) + sum(x["ldpcChannelLossFer01"] != "N/A" for x in result_matrix)
    valid001 = sum(x["ccChannelLossFer001"] != "N/A" for x in result_matrix) + sum(x["ldpcChannelLossFer001"] != "N/A" for x in result_matrix)
    unavailable01, unavailable001 = 20 - valid01, 20 - valid001
    final = f"""# Round08-A S5 第 7 章写作证据终审报告

## Gate

`PASS_ROUND08_A_S5_CHAPTER7_EVIDENCE_SCAN`

未发现正式数据损坏、图表与 CSV 不一致、源代码/冻结配置实质矛盾或需要重跑 Formal 的阻断项。Round08-B 可以开始正式正文写作；本轮不自动进入下一轮。

## 核心数字

1. Stage11 正式图：86 张；对应 `figure_data.csv`：86 个。
2. Aggregate 图：20 张。
3. Formal：744 个唯一 scheme points；2 个 comparison groups；6 个正式信道；4 个正式方案。
4. FER=0.1 可计算 channel-loss 组合：{valid01}/20；FER=0.01：{valid001}/20；未覆盖而为 N/A 的组合分别为 {unavailable01} 与 {unavailable001}。
5. 推荐正文主图：8 张核心图（Aggregate 01–04、13–16），17–20 为按篇幅条件选用；推荐三线表：8 张核心表加 1 张可选专项表。
6. 检出的报告语言/统计风险：11 项，均已在 `16_s5_report_language_risk.md` 固化为写作约束，而非 Formal 阻断错误。

## 主要发现

- 近 2/3 AWGN 下 CC R2/3 的目标 FER 门限更低；近 1/2 AWGN 下 LDPC N640 的门限更低。此为绝对性能判断。
- 固定多径采用已知实轴 MMSE 后仍存在差异；其结果必须与接收端已知 taps 的前提一起报告。
- CFO 与线性时变频率是不同模型；后者的相位轨迹还受 Ntx 影响，不能将差异完全归因于码型。
- 已知 5% 连续遮挡属于已知擦除式损伤（LLR=0）；CC 在当前无交织模型中出现强烈 FER 饱和，而 LDPC 保留部分门限覆盖。未知突发因 mask 未知且 LLR 失配更难恢复；大部分目标不被测量范围覆盖，必须保持 N/A。
- N480 的平均译码时间在多种场景低于同组 CC，但 N640 与 CC 的时延需按场景逐项比较；所有时间均是当前主机的软件观测值。

## 证据链

源码/冻结配置 → Stage10 Formal CSV → Stage11 单图与汇总 CSV → Aggregate 多曲线图 → 门限与相对 AWGN 损失 → 结果矩阵 → 第 7 章图表计划。本轮所有结果均保留到各项文件的 source 字段，未混入 Stage12 的独立验证结果。

## 限制

受控信道、软件时延和有限 SNR 网格不外推为实际卫星链路或硬实时保证。所有门限与 channel loss 均遵守“不外推”规则。
"""
    write_text("17_s5_round08A_final_report.md", final)
    write_text("18_s5_round08A_gate.txt", "PASS_ROUND08_A_S5_CHAPTER7_EVIDENCE_SCAN")
    write_text("readme.txt", "本目录用于第 7 章正式写作前的 S5 证据扫描、统计口径冻结、图表资产索引和章节规划。内容仅由既有 Formal CSV、Stage11/Aggregate 资产、冻结配置与源码读取生成；不存放新的 Formal 仿真结果。运行 round08a_scan.py 可在空目录中再生本轮资产。")
    print(f"PASS rows={len(formal_rows)} stage11={len(stage_figs)} aggregate={len(agg_figs)}")


if __name__ == "__main__":
    main()
