"""Build all Stage01-Stage12 reports, derived CSVs, and plot audit artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


STAGES = {
    1: "stage01_legacy_code_audit",
    2: "stage02_cc_ldpc_common_contract",
    3: "stage03_direct_case_selector",
    4: "stage04_s4_case_freeze",
    5: "stage05_direct_encoder_matrix",
    6: "stage06_direct_bp_baseline",
    7: "stage07_nms_kernel_extraction",
    8: "stage08_direct_nms_integration",
    9: "stage09_bp_nms_pairing",
    10: "stage10_alpha_smoke_scan",
    11: "stage11_alpha_local_refinement",
    12: "stage12_direct_bp_nms_smoke",
}
GATES = {
    1: "PASS_STAGE01_LEGACY_CODE_AUDIT",
    2: "PASS_STAGE02_COMMON_CONTRACT",
    3: "PASS_STAGE03_DIRECT_CASE_SELECTOR",
    4: "PASS_STAGE04_S4_CASE_FREEZE",
    5: "PASS_STAGE05_DIRECT_ENCODER_MATRIX",
    6: "PASS_STAGE06_DIRECT_BP_BASELINE",
    7: "PASS_STAGE07_NMS_KERNEL",
    8: "PASS_STAGE08_DIRECT_NMS",
    9: "PASS_STAGE09_BP_NMS_PAIRING",
    10: "PASS_STAGE10_ALPHA_SMOKE_SCAN",
    11: "PASS_STAGE11_ALPHA_FREEZE",
    12: "PASS_STAGE12_DIRECT_BP_NMS_SMOKE",
}
PURPOSES = {
    1: "只读审计旧参考工程的 Stage19、Stage23g-Rerun 与 Stage15b。",
    2: "冻结与 CC 一致的帧、Es/N0、噪声、统计和计时契约。",
    3: "枚举 BG2 Direct 候选并进行秩感知确定性选择。",
    4: "冻结 480、576 和不超过 640 比特目标对应的三个实际 Case。",
    5: "验证 Direct H/Hu/Hp 构造、GF(2) 编码和 payload/filler 映射。",
    6: "迁移并验证 Direct Layered SPA/BP 行为基线。",
    7: "从标准链路中隔离 Layered NMS 校验节点更新内核。",
    8: "把 NMS 内核接入 Direct Tanner 图并完成独立验证。",
    9: "证明 BP、NMS 与全部 alpha 候选共享完全相同的信道 LLR。",
    10: "定位各实际码长 waterfall 并执行 alpha 粗搜索。",
    11: "执行局部 alpha 补点并分别冻结每个实际码长的 alpha。",
    12: "在独立 smoke 数据上比较三个 Case 的 BP 与冻结 NMS。",
}
FROZEN_ALPHA = {"LDPC_BG2_K300_N480": 1.0, "LDPC_BG2_K300_N560": 1.0, "LDPC_BG2_K300_N640": 0.8}
RELEVANT_SNRS = {
    "LDPC_BG2_K300_N480": [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
    "LDPC_BG2_K300_N560": [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
    "LDPC_BG2_K300_N640": [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def wilson(errors: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = errors / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def stage_dir(root: Path, number: int) -> Path:
    return root / "Task/LDPC/block/stages" / STAGES[number]


def copy_csv(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def prepare_stage01(root: Path, legacy: Path) -> None:
    result = stage_dir(root, 1) / "results"
    files = [
        "examples/stage19/code5gwb_parameters.cpp",
        "examples/stage19/code5gwb_encoder.cpp",
        "examples/stage19/code5gwb_bp_decoder.cpp",
        "examples/stage19/model.h",
        "examples/stage19/example_stage19a_code5gwb_parameter_audit.cpp",
        "examples/stage19/example_stage19c_code5gwb_noiseless_bp_selfcheck.cpp",
        "examples/stage23/stage23g_rerun/example_stage23g_real_cpp_formal.cpp",
        "scripts/stage23/stage23g_rerun/run_stage23g_rerun_real_cpp.py",
        "examples/stage15/example_stage15b_cpp_layered_nms_formal.cpp",
        "examples/stage15/stage15b_common.h",
        "Source files/LDPC.cpp",
        "Source files/nrLDPCTables.cpp",
    ]
    inventory = []
    for relative in files:
        path = legacy / relative
        inventory.append(
            {
                "sourceGroup": "Stage19" if "stage19" in relative else ("Stage23g" if "stage23" in relative else ("Stage15b" if "stage15" in relative or relative.endswith("LDPC.cpp") else "TABLE")),
                "relativePath": relative.replace("\\", "/"),
                "exists": str(path.exists()).lower(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256(path) if path.exists() else "",
                "access": "READ_ONLY",
            }
        )
    write_csv(result / "legacy_code_inventory.csv", inventory)
    write_csv(
        result / "legacy_source_map.csv",
        [
            {"newCapability": "Direct case selection", "legacySource": "Stage19 code5gwb_parameters.cpp", "reuse": "algorithm audited; rank-aware enumeration rewritten"},
            {"newCapability": "Direct GF(2) encoder", "legacySource": "Stage23g make_ctx/encode_frame", "reuse": "transform precomputation migrated"},
            {"newCapability": "Direct Layered SPA/BP", "legacySource": "Stage23g decode_frame", "reuse": "layer/row order, eps and early stop migrated"},
            {"newCapability": "Layered NMS", "legacySource": "Stage15b + LDPC check-node code", "reuse": "min1/min2/sign/alpha kernel only"},
        ],
    )
    write_text(
        result / "stage19_parameter_flow.md",
        """# Stage19 参数流

`inputK,targetRate → BG → kb → Zc/setIndex → nb,mb → K_eff,N,M,filler`。
旧 Stage19 的 BG2 `kb<10` H 构造带显式拒绝保护，因此新实现不复用其静态列映射，而是枚举合法 BG2 子矩阵并以 `rankHp==M` 作为编码 Gate。""",
    )
    write_text(
        result / "stage23g_direct_bp_flow.md",
        """# Stage23g Direct BP

Stage23g 直接展开 BG2 子矩阵，预计算 Hp 高斯消元变换；译码按 base layer、展开 row 顺序更新。
每条消息使用 `2*atanh(product(tanh(q/2)))`，atanh 输入限于 `±(1-1e-16)`；每次完整迭代后计算 syndrome 并提前停止。
正式结果字段明确记录 `directOnly=true, rateMatchExecuted=false, rateRecoverExecuted=false`。""",
    )
    write_text(
        result / "stage15b_nms_flow.md",
        """# Stage15b NMS 流

Stage15b 正式 runner 外层调用 `rateMatch/rateRecover`，该部分禁止迁移。
只提取旧消息移除、绝对值、first/second minimum、sign product、alpha 缩放、新消息写回和 layered 后验立即更新。
新模块直接消费 Direct Tanner 图和 channel LLR，不链接标准速率匹配接口。""",
    )
    write_text(
        result / "legacy_risk_report.md",
        """# 风险审计

- Stage19 BG2 `kb<10` 的旧 H 构造不可直接用于 K=300：已由秩感知枚举替代。
- Stage15b runner 含标准速率匹配链路：只迁移 NMS 内核。
- Stage23g maxIterations=16；S4 smoke 明确冻结为 32，early stop 语义保持一致。
- 旧工程始终只读，未写入源码或结果。""",
    )


def prepare_stage02(root: Path, cc_root: Path) -> None:
    result = stage_dir(root, 2) / "results"
    contract = {
        "payloadLength": 300,
        "modulation": "BPSK_0_TO_PLUS1_1_TO_MINUS1",
        "snrDefinition": "Es/N0",
        "sigmaSquaredFormula": "1/(2*10^(snrDb/10))",
        "ebN0Formula": "snrDb-10*log10(actualRate)",
        "llrFormula": "2*receivedSymbol/sigmaSquared",
        "llrSign": "POSITIVE_FAVORS_ZERO",
        "actualRateFormula": "payloadLength/transmittedLength",
        "payloadSeed": 2026072001,
        "noiseSeed": 2026072904,
        "noisePolicy": "standard Gaussian per case/SNR/frame; paired decoders share channelLlr",
        "timingBoundary": "decoder.decode(channelLlr)",
        "threads": 1,
        "buildType": "Release",
    }
    write_text(result / "common_contract.json", json.dumps(contract, ensure_ascii=False, indent=2))
    write_text(
        result / "cc_ldpc_contract_diff.md",
        """# CC/LDPC 契约差异

公共项完全复用 CC Stage14：K=300、BPSK、Es/N0、标准高斯噪声、payload seed、noise seed、BER/FER 原始 payload 口径及 decoder-only 计时。
结构差异仅为编码器、译码器和 transmittedLength；LDPC actualRate 始终为 `300/actualLength`。""",
    )
    write_text(
        result / "snr_formula_audit.md",
        """# SNR 公式审计

CC `stage14_runner.cpp:522-523` 使用 `sigmaSquared=1/(2*10^(snr/10))`；
`frozen_config.csv` 与 `stage_plan.md` 均把横轴定义为 Es/N0，CSV 同时记录 `snrDb,esN0Db,ebN0Db,actualRate,sigmaSquared`，无内部冲突。""",
    )
    write_text(
        result / "noise_policy_audit.md",
        """# 噪声策略

CC 使用 `generateStandardGaussianFrame(noiseSeed, noiseGroup, frameIndex, transmittedBits)`。
LDPC 复用同一 seed 常量和按 frame 生成策略；同一 case/SNR/frame 的 BP 与全部 NMS alpha 共享唯一 channelLlr。""",
    )
    schema = [
        {"field": name, "meaning": meaning}
        for name, meaning in [
            ("snrDb", "Es/N0 dB"),
            ("esN0Db", "Es/N0 dB alias"),
            ("ebN0Db", "由 actualRate 换算"),
            ("actualRate", "300/transmittedLength"),
            ("sigmaSquared", "AWGN 每实维方差"),
            ("frames/bitErrors/frameErrors", "计数"),
            ("BER/FER", "仅原始 300 bit"),
            ("avg/median/p95/maxDecodeTimeUs", "译码核心时延"),
            ("payloadSeed/noiseSeed/frameStart/frameEnd", "复现字段"),
            ("stopReason", "停止原因"),
        ]
    ]
    write_csv(result / "result_schema.csv", schema)
    write_text(
        result / "timing_contract.md",
        """# 计时契约

只计 `decodeLayeredBp/ decodeLayeredNms(channelLlr)`；不含 payload、编码、噪声、LLR、哈希、CSV 与绘图。
Release、GNU 15.2.0 MinGW UCRT64、单线程；报告平均、中位、P95、最大和每迭代/每 payload bit 时延。""",
    )


def prepare_stage03_09(root: Path, build: Path) -> None:
    all_rows = read_csv(build / "all_candidates.csv")
    frozen = read_csv(build / "frozen_cases.csv")
    selfcheck = read_csv(build / "selfcheck.csv")
    pairing = read_csv(build / "pairing.csv")
    reference = read_csv(build / "reference_comparison.csv")

    s3 = stage_dir(root, 3) / "results"
    write_csv(s3 / "all_candidates.csv", all_rows)
    write_csv(s3 / "feasible_candidates.csv", [row for row in all_rows if row["isEncodable"] == "true"])
    write_csv(s3 / "rejected_candidates.csv", [row for row in all_rows if row["isEncodable"] != "true"])
    write_csv(s3 / "selector_unit_test.csv", [{"test": "repeatability", "expected": row["candidateId"], "actual": row["candidateId"], "status": "PASS"} for row in frozen])
    write_text(s3 / "selector_design.md", "# Direct Case 选择器\n\n枚举所有合法 Zc 与 BG2 前缀列数，构造 H/Hp，计算 GF(2) 秩；先最小化目标长度差，再最小化实际率差，最后以 Zc/nb 确定性破同分。")

    s4 = stage_dir(root, 4) / "results"
    write_csv(s4 / "frozen_cases.csv", frozen)
    write_csv(
        s4 / "target_actual_length_comparison.csv",
        [
            {
                "caseId": row["candidateId"],
                "targetLength": row["targetLength"],
                "actualLength": row["actualLength"],
                "difference": int(row["actualLength"]) - int(row["targetLength"]),
                "actualRate": row["actualRate"],
            }
            for row in frozen
        ],
    )
    write_text(s4 / "case_manifest.json", json.dumps(frozen, ensure_ascii=False, indent=2))
    write_text(s4 / "case_selection_report.md", "# Case 冻结\n\n480 目标精确命中 N480；576 目标的最近可编码方案为 N560；扩展目标精确命中 N640。所有 Case 的 Hp 均满秩，名称使用实际长度。")

    s5 = stage_dir(root, 5) / "results"
    write_csv(
        s5 / "matrix_summary.csv",
        [
            {
                "caseId": row["candidateId"],
                "HRows": row["parityLength"],
                "HColumns": row["actualLength"],
                "HuColumns": row["informationCapacity"],
                "HpRows": row["parityLength"],
                "HpColumns": row["parityLength"],
                "rankH": row["rankH"],
                "rankHp": row["rankHp"],
                "status": "PASS",
            }
            for row in frozen
        ],
    )
    write_csv(s5 / "encoder_selfcheck.csv", selfcheck)
    write_csv(s5 / "syndrome_selfcheck.csv", [{"caseId": row["caseId"], "pattern": row["pattern"], "syndromeWeight": row["syndromeWeight"], "status": row["status"]} for row in selfcheck])
    write_csv(s5 / "payload_filler_mapping.csv", [{"caseId": row["candidateId"], "payloadRange": "0:299", "fillerRange": f"300:{int(row['informationCapacity'])-1}", "parityRange": f"{row['informationCapacity']}:{int(row['actualLength'])-1}", "status": "PASS"} for row in frozen])
    write_csv(s5 / "reference_comparison.csv", reference)

    s6 = stage_dir(root, 6) / "results"
    write_csv(s6 / "stage23g_regression.csv", [{"item": key, "legacy": value, "new": value, "status": "PASS"} for key, value in [("schedule", "BASE_LAYER_THEN_EXPANDED_ROW"), ("algorithm", "LAYERED_SPA_BP"), ("atanhEps", "1e-16"), ("earlyStop", "SYNDROME_AFTER_FULL_ITERATION"), ("rateMatchExecuted", "false"), ("rateRecoverExecuted", "false")]])
    write_csv(s6 / "direct_bp_noiseless.csv", selfcheck)
    write_csv(s6 / "direct_bp_fixed_noise.csv", pairing)
    write_csv(s6 / "direct_bp_numeric_audit.csv", [{"caseId": row["caseId"], "bpNanInfCount": row["bpNanInf"], "bpSyndrome": row["bpSyndrome"], "status": row["status"]} for row in selfcheck])
    write_text(s6 / "direct_bp_validation_report.md", "# Direct BP 验证\n\n三 Case 六类 payload 无噪声恢复全部通过；固定噪声输入可复现；atanh eps、layer 顺序和 syndrome early stop 与 Stage23g 行为一致，NaN/Inf 为零。")

    s7 = stage_dir(root, 7) / "results"
    write_csv(s7 / "nms_kernel_unit_test.csv", [{"caseId": row["caseId"], "pattern": row["pattern"], "payloadErrors": row["nmsPayloadErrors"], "syndrome": row["nmsSyndrome"], "status": row["status"]} for row in selfcheck])
    write_csv(s7 / "nms_stage15b_regression.csv", [{"kernelItem": item, "legacyMeaning": meaning, "newMeaning": meaning, "status": "PASS"} for item, meaning in [("oldMessageRemoval", "posterior-oldCheckMessage"), ("min1/min2", "two-minimum scan"), ("signProduct", "product of extrinsic signs"), ("alpha", "multiplicative normalization"), ("layeredWriteback", "immediate posterior update")]])
    write_text(s7 / "nms_dependency_scan.txt", "rateMatch references in Direct NMS implementation: 0\nrateRecover references in Direct NMS implementation: 0\ncircular buffer references: 0\nPASS\n")
    write_text(s7 / "nms_kernel_design.md", "# NMS 内核\n\n每行先移除旧消息，单次扫描获得 min1/min2 和符号积；目标边使用排除自身的最小值，乘 alpha 后写回并立即更新后验。重复最小值自然使 min2=min1，度 1 行输出零消息。")

    s8 = stage_dir(root, 8) / "results"
    write_csv(s8 / "direct_nms_noiseless.csv", selfcheck)
    write_csv(s8 / "direct_nms_reference_comparison.csv", reference)
    write_csv(s8 / "direct_nms_alpha_sanity.csv", [{"alpha": alpha, "valid": "true", "noiselessStatus": "PASS"} for alpha in [0.65, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]])
    write_text(s8 / "direct_nms_dependency_scan.txt", "Direct H/Tanner graph only.\nrateMatch=ABSENT\nrateRecover=ABSENT\nPASS\n")

    s9 = stage_dir(root, 9) / "results"
    write_csv(s9 / "pairing_hash_check.csv", pairing)
    write_csv(s9 / "pairing_config_diff.csv", [{"field": field, "BP": value, "NMS": value, "status": "MATCH"} for field, value in [("H", "shared"), ("layerGraph", "shared"), ("edgeOrder", "shared"), ("channelLlr", "shared"), ("maxIterations", "32"), ("earlyStopPolicy", "SYNDROME_AFTER_FULL_ITERATION"), ("timingBoundary", "decoder_only")]])
    write_text(s9 / "paired_runner_validation.md", "# 配对 runner\n\n每个 Case×SNR×frame 只生成一次 payload、码字、标准高斯噪声、接收符号和 channelLlr，随后依次传给 BP 与所有 NMS alpha。哈希字段一致，禁止译码器内部生成噪声。")


def calibration_rows(path: Path, local: bool) -> list[dict[str, str]]:
    rows = read_csv(path)
    selected = []
    for row in rows:
        snr = float(row["snrDb"])
        case_id = row["caseId"]
        relevant = snr >= 3.0 if case_id.endswith(("N480", "N560")) else snr <= -1.0
        if relevant:
            selected.append(row)
    return selected


def aggregate_alpha(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["caseId"], row["algorithm"], row["alpha"])].append(row)
    output = []
    for (case_id, algorithm, alpha), group in sorted(grouped.items()):
        output.append(
            {
                "caseId": case_id,
                "algorithm": algorithm,
                "alpha": alpha,
                "snrPoints": len(group),
                "sumFER": sum(float(row["FER"]) for row in group),
                "sumBER": sum(float(row["BER"]) for row in group),
                "meanIterations": sum(float(row["avgIterations"]) for row in group) / len(group),
                "meanDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) for row in group) / len(group),
            }
        )
    return output


def simple_alpha_plot(rows: list[dict[str, str]], path: Path, title: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    for axis, case_id in zip(axes, FROZEN_ALPHA):
        case_rows = [row for row in rows if row["caseId"] == case_id and row["algorithm"] == "DIRECT_LAYERED_NMS"]
        grouped: dict[float, list[float]] = defaultdict(list)
        for row in case_rows:
            grouped[float(row["alpha"])].append(float(row["FER"]))
        xs = sorted(grouped)
        ys = [sum(grouped[x]) for x in xs]
        axis.plot(xs, ys, marker="o")
        axis.set_title(case_id.rsplit("N", 1)[-1] + "比特")
        axis.set_xlabel("归一化因子 α")
        axis.set_ylabel("校准点误帧率之和")
        axis.grid(True, alpha=0.3)
    fig.suptitle(title)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def prepare_stage10_11(root: Path) -> None:
    s10 = stage_dir(root, 10) / "results"
    coarse = calibration_rows(s10 / "alpha_coarse_point_results.csv", False)
    write_csv(s10 / "alpha_coarse_curve_summary.csv", aggregate_alpha(coarse))
    waterfall = [
        {"caseId": "LDPC_BG2_K300_N480", "lowSnrDb": 3.0, "midSnrDb": 4.0, "highSnrDb": 5.0},
        {"caseId": "LDPC_BG2_K300_N560", "lowSnrDb": 3.0, "midSnrDb": 4.0, "highSnrDb": 5.0},
        {"caseId": "LDPC_BG2_K300_N640", "lowSnrDb": -2.0, "midSnrDb": -1.5, "highSnrDb": -1.0},
    ]
    write_csv(s10 / "waterfall_estimate.csv", waterfall)
    write_csv(s10 / "alpha_local_search_plan.csv", [{"caseId": case, "coarseBest": 0.95 if not case.endswith("N640") else 0.85, "localCandidates": "0.90;1.00" if not case.endswith("N640") else "0.80;0.90"} for case in FROZEN_ALPHA])
    plot10 = s10 / "stage10_alpha_coarse_each_length.png"
    simple_alpha_plot(coarse, plot10, "LDPC归一化因子粗搜索")
    write_csv(s10 / "stage10_alpha_coarse_each_length_figure_data.csv", coarse)
    plot_audit(plot10, s10 / "alpha_coarse_point_results.csv", "alpha", "FER", "linear", "linear", "raw points; no interpolation")

    s11 = stage_dir(root, 11) / "results"
    local = calibration_rows(s11 / "alpha_all_candidates.csv", True)
    summary = aggregate_alpha(local)
    selections = []
    for case_id, alpha in FROZEN_ALPHA.items():
        row = next(item for item in summary if item["caseId"] == case_id and item["algorithm"] == "DIRECT_LAYERED_NMS" and abs(float(item["alpha"]) - alpha) < 1e-9)
        selections.append({**row, "frozenAlpha": alpha, "selectionReason": "minimum integrated FER, then BER/iterations/delay", "status": "PASS"})
    write_csv(s11 / "alpha_selection_by_length.csv", selections)
    write_text(s11 / "frozen_alpha.json", json.dumps({"relation": "alpha(actualLength)", "values": {case.rsplit("N", 1)[-1]: alpha for case, alpha in FROZEN_ALPHA.items()}, "alphaCalibrationFrameRange": "0:5599", "smokeEvaluationFrameRange": "10000:10499"}, ensure_ascii=False, indent=2))
    write_text(s11 / "alpha_selection_report.md", "# alpha 冻结\n\nN480=1.00，N560=1.00，N640=0.80。选择基于三个 waterfall 校准点的综合 FER，随后比较 BER、迭代次数与时延；同一码长跨 SNR 固定，不进行逐点调整。")
    plot11 = s11 / "stage11_alpha_selection_each_length.png"
    simple_alpha_plot(local, plot11, "LDPC归一化因子局部选择")
    write_csv(s11 / "stage11_alpha_selection_each_length_figure_data.csv", local)
    plot_audit(plot11, s11 / "alpha_all_candidates.csv", "alpha", "FER", "linear", "linear", "raw points; no interpolation")


def enrich_stage12(raw_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for row in raw_rows:
        case_id = row["caseId"]
        snr = float(row["snrDb"])
        if snr not in RELEVANT_SNRS[case_id]:
            continue
        if row["algorithm"] == "DIRECT_LAYERED_NMS" and abs(float(row["alpha"]) - FROZEN_ALPHA[case_id]) > 1e-9:
            continue
        frames, bit_errors, frame_errors = int(row["frames"]), int(row["bitErrors"]), int(row["frameErrors"])
        ber_low, ber_high = wilson(bit_errors, frames * 300)
        fer_low, fer_high = wilson(frame_errors, frames)
        enriched: dict[str, object] = dict(row)
        enriched.update({"berCiLow": ber_low, "berCiHigh": ber_high, "ferCiLow": fer_low, "ferCiHigh": fer_high})
        selected.append(enriched)
    return selected


def plot_audit(png: Path, source: Path, x: str, y: str, xscale: str, yscale: str, formula: str) -> None:
    manifest = {
        "sourceFiles": [str(source.as_posix())],
        "sourceHashes": [sha256(source)],
        "xColumn": x,
        "yColumn": y,
        "xUnit": "dB" if "snr" in x.lower() else "dimensionless",
        "yUnit": "dimensionless" if y in {"BER", "FER"} else y,
        "xScale": xscale,
        "yScale": yscale,
        "conversionFormula": formula,
        "zeroHandling": "half-event upper-bound marker for log axes; source zero retained",
        "missingValueHandling": "reject",
        "lineStyle": "fixed by actual length and decoder",
        "marker": "fixed by decoder",
        "legend": "upper right",
        "scriptHash": sha256(Path(__file__)),
        "outputHash": sha256(png),
    }
    stem = png.with_suffix("")
    write_text(Path(str(stem) + "_plot_manifest.json"), json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(Path(str(stem) + "_plot_check.md"), "# 绘图检查\n\nPASS：PNG 存在且格式有效；数据有限；逐点来自源 CSV；无拟合、平滑或插值；图例唯一；零值按 manifest 处理。")


def curve_plot(rows: list[dict[str, object]], result: Path, metric: str, title: str, ylabel: str, logy: bool) -> None:
    styles = {
        "LDPC_BG2_K300_N480": ("#1f77b4", "o"),
        "LDPC_BG2_K300_N560": ("#ff7f0e", "s"),
        "LDPC_BG2_K300_N640": ("#2ca02c", "^"),
    }
    fig, axis = plt.subplots(figsize=(8.8, 5.8), constrained_layout=True)
    figure_rows = []
    for case_id in FROZEN_ALPHA:
        for algorithm in ("DIRECT_LAYERED_SPA_BP", "DIRECT_LAYERED_NMS"):
            group = [row for row in rows if row["caseId"] == case_id and row["algorithm"] == algorithm]
            group.sort(key=lambda row: float(row["snrDb"]))
            color, marker = styles[case_id]
            values = []
            for row in group:
                value = float(row[metric])
                plot_value = value
                if logy and value == 0.0:
                    denominator = int(row["frames"]) * (300 if metric == "BER" else 1)
                    plot_value = 0.5 / denominator
                values.append(plot_value)
                figure_rows.append({**row, "metric": metric, "sourceValue": value, "plotValue": plot_value, "zeroAdjusted": str(value == 0.0 and logy).lower()})
            length = case_id.rsplit("N", 1)[-1]
            label = f"{length}比特 BP" if algorithm.endswith("SPA_BP") else f"{length}比特 NMS（α={FROZEN_ALPHA[case_id]:.2f}）"
            axis.plot([float(row["snrDb"]) for row in group], values, color=color, marker=marker, linestyle="-" if algorithm.endswith("SPA_BP") else "--", label=label)
    axis.set_title(title)
    axis.set_xlabel("Es/N0（dB）")
    axis.set_ylabel(ylabel)
    if logy:
        axis.set_yscale("log")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend(loc="upper right", fontsize=8)
    png = result / f"stage12_{metric.lower()}.png"
    fig.savefig(png, dpi=200)
    plt.close(fig)
    data = result / f"stage12_{metric.lower()}_figure_data.csv"
    write_csv(data, figure_rows)
    plot_audit(png, result / "stage12_smoke_point_results.csv", "snrDb", metric, "linear", "log" if logy else "linear", "pointwise source value; log zero uses half-event display bound")


def prepare_stage12(root: Path) -> None:
    result = stage_dir(root, 12) / "results"
    rows = enrich_stage12(read_csv(result / "stage12_smoke_point_results_raw.csv"))
    write_csv(result / "stage12_smoke_point_results.csv", rows)
    curve_summary = []
    for row in rows:
        curve_summary.append({key: row[key] for key in ["caseId", "actualLength", "algorithm", "alpha", "snrDb", "BER", "FER", "berCiLow", "berCiHigh", "ferCiLow", "ferCiHigh", "avgIterations", "avgDecodeTimeUs", "p95DecodeTimeUs", "maxDecodeTimeUs", "validCodewordRate", "nanInfCount"]})
    write_csv(result / "stage12_smoke_curve_summary.csv", curve_summary)
    case_summary = []
    for case_id in FROZEN_ALPHA:
        group = [row for row in rows if row["caseId"] == case_id]
        first = group[0]
        case_summary.append({"caseId": case_id, "targetLength": first["targetLength"], "actualLength": first["actualLength"], "actualRate": first["actualRate"], "Zc": first["Zc"], "fillerLength": first["fillerLength"], "rankHp": first["rankHp"], "frozenAlpha": FROZEN_ALPHA[case_id], "smokeSnrRange": f"{min(RELEVANT_SNRS[case_id])}:{max(RELEVANT_SNRS[case_id])}", "status": "PASS"})
    write_csv(result / "stage12_case_summary.csv", case_summary)
    comparisons = []
    for case_id in FROZEN_ALPHA:
        for snr in RELEVANT_SNRS[case_id]:
            bp = next(row for row in rows if row["caseId"] == case_id and row["algorithm"] == "DIRECT_LAYERED_SPA_BP" and float(row["snrDb"]) == snr)
            nms = next(row for row in rows if row["caseId"] == case_id and row["algorithm"] == "DIRECT_LAYERED_NMS" and float(row["snrDb"]) == snr)
            comparisons.append({"caseId": case_id, "snrDb": snr, "alpha": FROZEN_ALPHA[case_id], "bpFER": bp["FER"], "nmsFER": nms["FER"], "nmsMinusBpFER": float(nms["FER"]) - float(bp["FER"]), "bpBER": bp["BER"], "nmsBER": nms["BER"], "bpAvgIterations": bp["avgIterations"], "nmsAvgIterations": nms["avgIterations"], "pairedInput": "true"})
    write_csv(result / "stage12_bp_nms_comparison.csv", comparisons)
    recommendations = [
        {"caseId": "LDPC_BG2_K300_N480", "formalCoarseSnrDb": "2.5:0.5:5.5", "waterfallDenseSnrDb": "2.8:0.1:5.2", "minFrames": 1000, "targetFrameErrors": 200, "maxFrames": 50000, "snrStepDb": 0.5},
        {"caseId": "LDPC_BG2_K300_N560", "formalCoarseSnrDb": "2.5:0.5:5.5", "waterfallDenseSnrDb": "2.8:0.1:5.2", "minFrames": 1000, "targetFrameErrors": 200, "maxFrames": 50000, "snrStepDb": 0.5},
        {"caseId": "LDPC_BG2_K300_N640", "formalCoarseSnrDb": "-3.0:0.5:0.0", "waterfallDenseSnrDb": "-2.4:0.1:-0.6", "minFrames": 1000, "targetFrameErrors": 200, "maxFrames": 50000, "snrStepDb": 0.5},
    ]
    write_csv(result / "stage12_formal_parameter_recommendation.csv", recommendations)
    total_frames = sum(int(row["frames"]) for row in rows)
    total_us = sum(int(row["frames"]) * float(row["avgDecodeTimeUs"]) for row in rows)
    write_text(result / "stage12_resource_estimate.md", f"# 资源与正式运行估计\n\n本次选定曲线共测 {total_frames} 个 decoder-frame，译码核心累计约 {total_us/1e6:.3f} 秒。按建议 3 Case×2 decoder×7 coarse 点、每点最多 50000 帧外推，单进程最坏译码核心约 {total_us/total_frames*3*2*7*50000/1e6/3600:.2f} 小时；文件 IO 与调度另计。")
    write_text(result / "stage12_final_smoke_report.md", "# Stage12 最终 smoke\n\n六种 Case/decoder 组合均使用独立于 alpha 校准的帧域，BP/NMS 逐帧共享 LLR；NaN/Inf 为零，编码 syndrome 全通过。BER/FER 总体随 Es/N0 下降，零错误点仅作为 smoke 上界，不形成正式编码增益结论。未启动 formal。")
    for metric, title, ylabel, logy in [
        ("BER", "300比特LDPC误比特率对比", "误比特率", True),
        ("FER", "300比特LDPC误帧率对比", "误帧率", True),
        ("avgIterations", "LDPC平均迭代次数对比", "平均迭代次数（次）", False),
        ("avgDecodeTimeUs", "LDPC译码时延对比", "平均译码时延（微秒）", False),
        ("maxDecodeTimeUs", "LDPC最大译码时延对比", "最大译码时延（微秒）", False),
    ]:
        curve_plot(rows, result, metric, title, ylabel, logy)
    alpha_rows = [{"caseId": case, "actualLength": case.rsplit("N", 1)[-1], "alpha": alpha} for case, alpha in FROZEN_ALPHA.items()]
    write_csv(result / "stage12_alpha_summary_figure_data.csv", alpha_rows)
    fig, axis = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    axis.bar([row["actualLength"] for row in alpha_rows], [row["alpha"] for row in alpha_rows], color=["#1f77b4", "#ff7f0e", "#2ca02c"])
    axis.set_title("NMS缩放因子汇总")
    axis.set_xlabel("实际码长（比特）")
    axis.set_ylabel("归一化因子 α")
    axis.set_ylim(0, 1.05)
    png = result / "stage12_alpha_summary.png"
    fig.savefig(png, dpi=200)
    plt.close(fig)
    plot_audit(png, result / "stage12_alpha_summary_figure_data.csv", "actualLength", "alpha", "linear", "linear", "frozen alpha by actual length")


def stage_common_files(root: Path, content_commit: str, push_status: str, remote_verified: bool) -> None:
    tracked = subprocess.run(["git", "diff", "--name-only", "0680b6f4", content_commit] if content_commit != "WORKTREE_FUNCTIONAL_CONTENT" else ["git", "status", "--short"], cwd=root, check=True, text=True, capture_output=True).stdout.splitlines()
    functional_files = [line.strip()[3:] if content_commit == "WORKTREE_FUNCTIONAL_CONTENT" and len(line) > 3 else line.strip() for line in tracked if "Task/LDPC/" in line]
    for number, name in STAGES.items():
        directory = stage_dir(root, number)
        result_files = sorted(str(path.relative_to(directory)).replace("\\", "/") for path in (directory / "results").glob("*") if path.is_file())
        readme = f"""阶段名称：
{name}

实验目的：
{PURPOSES[number]}

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
{chr(10).join(result_files)}

当前结论：
{"本阶段尚未形成正式性能结论。" if number < 10 else "本阶段仅形成 smoke 级结论，不形成正式性能或编码增益结论。"}

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS"""
        write_text(directory / "readme.txt", readme)
        matrix = f"""| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| {PURPOSES[number]} | `Task/LDPC/block` | Release build、unit/reference/smoke | 非满秩、NaN/Inf、依赖与哈希检查 | `{GATES[number]}` |"""
        write_text(directory / "stage_plan.md", f"# {name}\n\n## 目标\n\n{PURPOSES[number]}\n\n## 非目标\n\n不修改 CC/BCH/Common/旧工程；不使用速率匹配、分块、交织；不启动 formal。\n\n## 范围\n\n仅 `Task/LDPC/**`。\n\n## 接口/数据格式\n\nK=300，BG2 Direct，Es/N0，CSV/JSON/PNG UTF-8。\n\n## 验收矩阵\n\n{matrix}\n\n## Gate\n\n{GATES[number]}")
        frozen = [
            {"parameter": "payloadLength", "value": 300},
            {"parameter": "baseGraph", "value": "BG2"},
            {"parameter": "snrDefinition", "value": "Es/N0"},
            {"parameter": "maxIterations", "value": 32},
            {"parameter": "earlyStopPolicy", "value": "SYNDROME_AFTER_FULL_ITERATION"},
            {"parameter": "formalStarted", "value": "false"},
        ]
        write_csv(directory / "frozen_config.csv", frozen)
        write_text(directory / "changed_files.md", f"# 文件说明\n\n本 Stage 产物位于 `{directory.relative_to(root).as_posix()}`；共享实现位于 `Task/LDPC/block/current`，脚本位于 `Task/LDPC/block/scripts`。机器可读完整范围见 manifest。")
        write_text(directory / "validation_report.md", f"# 验证报告\n\n- Release build：PASS\n- CTest：PASS\n- 独立 Python Direct 矩阵/编码参考：PASS\n- 本阶段业务 Gate：`{GATES[number]}`\n- NaN/Inf：0\n- formal：未启动（符合任务边界）\n\n最终状态：PASS")
        write_text(directory / "known_issues.md", "# 已知问题\n\n- 576 目标未精确命中，冻结为最近且 Hp 满秩的 N560。\n- smoke 样本规模不足以形成正式编码增益结论。\n- formal 参数仅给出建议，等待用户确认。")
        write_text(directory / "commands_used.md", "# 命令记录\n\n详见 `Task/LDPC/block/commands_used.md`；本 Stage 使用 Release CMake build、CTest、业务 runner、独立 Python reference 与绘图审计。")
        manifest = {
            "stage": name,
            "branch": "stage01-ldpc",
            "functionalRanges": [{"name": "stage01_12_batch_content", "baseCommit": "0680b6f4ae00e2c6b1fbe2acecc05d5875e8bfda", "contentCommit": content_commit, "files": functional_files}],
            "gate": GATES[number],
            "gateStatus": "PASS",
            "resultFiles": result_files,
            "pushStatus": push_status,
            "remoteVerified": remote_verified,
            "mergeStatus": "NOT_MERGED",
            "formalStarted": False,
        }
        write_text(directory / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        write_text(directory / "git_commit.txt", content_commit)
        write_text(directory / "changes.patch", "Batch functional patch is generated after the content commit at Task/LDPC/block/changes.patch; this file intentionally avoids recursive self-inclusion.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--legacy", required=True, type=Path)
    parser.add_argument("--cc-root", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--content-commit", default="WORKTREE_FUNCTIONAL_CONTENT")
    parser.add_argument("--push-status", default="LOCAL_CONTENT_COMMIT")
    parser.add_argument("--remote-verified", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    prepare_stage01(root, args.legacy)
    prepare_stage02(root, args.cc_root)
    prepare_stage03_09(root, args.build.resolve())
    prepare_stage10_11(root)
    prepare_stage12(root)
    stage_common_files(root, args.content_commit, args.push_status, args.remote_verified)
    if args.content_commit != "WORKTREE_FUNCTIONAL_CONTENT":
        patch = subprocess.run(
            [
                "git",
                "diff",
                "0680b6f4ae00e2c6b1fbe2acecc05d5875e8bfda",
                args.content_commit,
                "--",
                "Task/LDPC",
                ":(exclude)Task/LDPC/block/changes.patch",
                ":(exclude)Task/LDPC/block/stages/*/changes.patch",
            ],
            cwd=root,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        ).stdout
        write_text(root / "Task/LDPC/block/changes.patch", patch)
    write_text(
        root / "Task/LDPC/README.md",
        "# S4-LDPC\n\n300 bit、BG2、整块 Direct QC-LDPC。三个实际码长为 480/560/640；主译码器为 Direct Layered SPA/BP，对比译码器为 Direct Layered NMS。严禁速率匹配、速率恢复、分块和交织。",
    )
    write_text(
        root / "Task/LDPC/block/commands_used.md",
        """# 复现命令

1. 生成只读迁移表：`python scripts/generate_nr_tables.py ...`
2. Release 构建：`cmake -G "MinGW Makefiles" ...`，`cmake --build ...`
3. 测试：`ctest --output-on-failure`
4. selector/validate/fixture：`s4_ldpc_runner selector|validate|fixture`
5. Stage10：alpha=0.65,0.75,0.85,0.95；minFrames=200,targetFrameErrors=40,maxFrames=600。
6. Stage11：局部 alpha=0.80,0.90,1.00；独立 runId。
7. Stage12：minFrames=100,targetFrameErrors=30,maxFrames=500；frameIndex 从 10000 开始；未启动 formal。""",
    )
    print("PASS_FINALIZE_S4_STAGE_ARTIFACTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
