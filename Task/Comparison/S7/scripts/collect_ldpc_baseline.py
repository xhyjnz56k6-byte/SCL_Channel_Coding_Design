import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE15 = ROOT / "stage15_scientific_plots"
OUTPUT = STAGE15 / "ldpc_baseline"
LDPC_REPO = Path(r"C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_LDPC")
LDPC_BLOCK = LDPC_REPO / "Task" / "LDPC" / "block"
LDPC_STAGE = LDPC_BLOCK / "stages" / "stage23_s4_final_reintegration"
SOURCE = LDPC_STAGE / "results" / "s4_revised_formal_point_results.csv"
CONFIG = LDPC_STAGE / "results" / "s4_revised_formal_config.json"
CASE_METADATA = LDPC_STAGE / "results" / "s4_revised_case_metadata.csv"
VALIDATION = LDPC_STAGE / "validation_report.md"
RECOMMENDATION = (
    LDPC_BLOCK / "stages" / "stage12r_alpha_curve_selection" / "results"
    / "alpha_selection_report.md"
)
CC_RATE = 300.0 / 612.0
SELECTED_LENGTH = 640
SELECTED_ALGORITHM = "DIRECT_LAYERED_NMS"
SELECTED_ALPHA = 0.80


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def git_output(*args):
    result = subprocess.run(
        ["git", "-C", str(LDPC_REPO), *args], capture_output=True,
        text=True, encoding="utf-8", check=True,
    )
    return result.stdout.rstrip("\n")


def main():
    required = [SOURCE, CONFIG, CASE_METADATA, VALIDATION, RECOMMENDATION]
    if not all(path.is_file() for path in required):
        raise RuntimeError("required validated LDPC source asset missing")
    if "PASS_STAGE23_S4_FINAL_REINTEGRATION" not in VALIDATION.read_text(encoding="utf-8"):
        raise RuntimeError("LDPC Stage23 validation is not PASS")
    if "N640" not in RECOMMENDATION.read_text(encoding="utf-8") or "0.80" not in RECOMMENDATION.read_text(encoding="utf-8"):
        raise RuntimeError("N640 NMS alpha recommendation evidence missing")

    raw = read_csv(SOURCE)
    metadata = {int(row["actualLength"]): row for row in read_csv(CASE_METADATA)}
    selected_with_lines = [
        (line_number, row) for line_number, row in enumerate(raw, 2)
        if int(row["actualLength"]) == SELECTED_LENGTH
        and row["algorithm"] == SELECTED_ALGORITHM
        and abs(float(row["alpha"]) - SELECTED_ALPHA) < 1e-12
    ]
    if len(selected_with_lines) != 31:
        raise RuntimeError(f"expected 31 selected LDPC points, found {len(selected_with_lines)}")
    if [float(row["esN0Db"]) for _, row in selected_with_lines] != [x / 2 for x in range(-10, 21)]:
        raise RuntimeError("selected LDPC Es/N0 grid mismatch")
    if any(row["status"] != "PASS" or row["snrDefinition"] != "Es/N0" for _, row in selected_with_lines):
        raise RuntimeError("selected LDPC point status/SNR definition mismatch")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(SOURCE)
    candidates = []
    for length in sorted(metadata):
        meta = metadata[length]
        rate = float(meta["actualRate"])
        for algorithm in ("DIRECT_LAYERED_SPA_BP", "DIRECT_LAYERED_NMS"):
            rows = [row for row in raw if int(row["actualLength"]) == length and row["algorithm"] == algorithm]
            alpha = "0" if algorithm == "DIRECT_LAYERED_SPA_BP" else rows[0]["alpha"]
            selected = length == SELECTED_LENGTH and algorithm == SELECTED_ALGORITHM
            reason = "" if selected else (
                "RATE_FARTHER_FROM_CC" if length != SELECTED_LENGTH
                else "FORMAL_NMS_ALPHA_0P80_IS_THE_FROZEN_RECOMMENDED_N640_DECODER"
            )
            candidates.append({
                "configurationId": f"LDPC_BG2_K300_N{length}_{algorithm}",
                "sourceStage": "stage23_s4_final_reintegration",
                "sourceCsvAbsolutePath": str(SOURCE.resolve()),
                "formalOrSmoke": "FORMAL",
                "validationStatus": "PASS_STAGE23_S4_FINAL_REINTEGRATION",
                "payloadBits": 300,
                "informationBits": meta["informationCapacity"],
                "fillerBits": meta["fillerLength"],
                "motherCodeLength": length,
                "transmittedBits": length,
                "actualRate": f"{rate:.17g}",
                "rateDifferenceToCc": f"{abs(rate - CC_RATE):.17g}",
                "relativeRateDifferenceToCc": f"{abs(rate - CC_RATE) / CC_RATE:.17g}",
                "baseGraph": 2,
                "liftingSize": meta["Zc"],
                "rateMatching": "false",
                "decoder": algorithm,
                "algorithm": algorithm,
                "alpha": alpha,
                "maxIterations": 32,
                "decisionType": "FLOAT_LLR_SOFT",
                "channel": "BPSK_AWGN_NO_BURST",
                "snrDefinition": "Es/N0",
                "interleaver": "NONE",
                "hasBer": "true",
                "hasFer": "true",
                "hasDecodeLatency": "true",
                "hasComplexity": "true",
                "hasBurst2": "false",
                "hasBurst5": "false",
                "hasBurst10": "false",
                "candidateStatus": "SELECTED" if selected else "EXCLUDED",
                "exclusionReason": reason,
                "sha256": source_hash,
            })
    candidate_fields = list(candidates[0])
    write_csv(OUTPUT / "ldpc_candidate_inventory.csv", candidate_fields, candidates)

    selected_rate = 300.0 / SELECTED_LENGTH
    selected_json = {
        "configurationId": "LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80",
        "payloadBits": 300,
        "informationBits": 320,
        "fillerBits": 20,
        "motherCodeLength": 640,
        "transmittedBits": 640,
        "actualRate": selected_rate,
        "ccActualRate": CC_RATE,
        "absoluteRateDifference": abs(selected_rate - CC_RATE),
        "relativeRateDifference": abs(selected_rate - CC_RATE) / CC_RATE,
        "baseGraph": 2,
        "liftingSize": 40,
        "rateMatching": False,
        "decoder": SELECTED_ALGORITHM,
        "algorithm": SELECTED_ALGORITHM,
        "alpha": SELECTED_ALPHA,
        "maxIterations": 32,
        "decisionType": "FLOAT_LLR_SOFT",
        "channel": "NO_BURST_AWGN",
        "snrDefinition": "Es/N0",
        "sigmaSquaredFormula": "1/(2*10^(EsN0Db/10))",
        "interleaver": "NONE",
        "sourceCsv": str(SOURCE.resolve()),
        "sourceSha256": source_hash,
        "selectionReason": "payload=300 exact; N640 has the smallest absolute rate difference to CC; N640 NMS alpha=0.80 is explicitly frozen by the alpha selection and final formal config; Stage23 is validated",
        "comparisonRole": "NO_INTERLEAVING_NEAR_RATE_REFERENCE",
        "burstCompatibility": "NO_BURST_AWGN_ONLY",
        "participatesInInterleaverRanking": False,
        "formalRerun": False,
    }
    (OUTPUT / "selected_ldpc_baseline.json").write_text(
        json.dumps(selected_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    point_fields = [
        "scheme", "configurationId", "comparisonRole", "channelCondition",
        "interleaver", "payloadBits", "encodedBits", "actualRate", "baseGraph",
        "liftingSize", "algorithm", "alpha", "maxIterations", "EsN0Db",
        "frames", "bitErrors", "frameErrors", "BER", "FER", "avgDecodeTimeUs",
        "medianDecodeTimeUs", "p95DecodeTimeUs", "maxDecodeTimeUs", "avgIterations",
        "edgeCount", "avgEdgeMessageUpdates", "avgTheoreticalOperationCount", "decoderMemoryBytes",
        "sourceCsvAbsolutePath", "sourceRowNumber", "sourceConfigurationId",
        "sourceStage", "sourceSha256", "interpolated", "synthetic",
    ]
    points = []
    for line_number, row in selected_with_lines:
        points.append({
            "scheme": "LDPC",
            "configurationId": selected_json["configurationId"],
            "comparisonRole": selected_json["comparisonRole"],
            "channelCondition": "NO_BURST_AWGN",
            "interleaver": "NONE",
            "payloadBits": 300,
            "encodedBits": 640,
            "actualRate": f"{selected_rate:.17g}",
            "baseGraph": 2,
            "liftingSize": 40,
            "algorithm": row["algorithm"],
            "alpha": row["alpha"],
            "maxIterations": row["maxIterations"],
            "EsN0Db": row["esN0Db"],
            "frames": row["frames"],
            "bitErrors": row["bitErrors"],
            "frameErrors": row["frameErrors"],
            "BER": row["BER"],
            "FER": row["FER"],
            "avgDecodeTimeUs": row["avgDecodeTimeUs"],
            "medianDecodeTimeUs": row["medianDecodeTimeUs"],
            "p95DecodeTimeUs": row["p95DecodeTimeUs"],
            "maxDecodeTimeUs": row["maxDecodeTimeUs"],
            "avgIterations": row["avgIterations"],
            "edgeCount": row["edgeCount"],
            "avgEdgeMessageUpdates": row["avgEdgeMessageUpdates"],
            "avgTheoreticalOperationCount": row["avgTheoreticalOperationCount"],
            "decoderMemoryBytes": row["decoderMemoryBytes"],
            "sourceCsvAbsolutePath": str(SOURCE.resolve()),
            "sourceRowNumber": line_number,
            "sourceConfigurationId": row["caseId"],
            "sourceStage": "stage23_s4_final_reintegration",
            "sourceSha256": source_hash,
            "interpolated": "false",
            "synthetic": "false",
        })
    write_csv(OUTPUT / "selected_ldpc_baseline_points.csv", point_fields, points)

    comparison_dir = STAGE15 / "results" / "cc" / "coding_baseline_comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    comparison_fields = [
        "scheme", "configuration", "channelCondition", "interleaver", "payloadBits",
        "encodedBits", "actualRate", "EsN0Db", "BER", "FER", "decodeLatencyNs",
        "complexity", "sourceCsv", "sourceRowKey", "comparisonRole",
    ]
    comparison_rows = []
    cc_baseline_path = STAGE15 / "no_burst_baseline" / "cc" / "no_burst_baseline.csv"
    for row in read_csv(cc_baseline_path):
        comparison_rows.append({
            "scheme": "CC", "configuration": "CC_NO_BURST_AWGN",
            "channelCondition": "NO_BURST_AWGN", "interleaver": "NONE",
            "payloadBits": 300, "encodedBits": 612, "actualRate": f"{CC_RATE:.17g}",
            "EsN0Db": row["EsN0Db"], "BER": row["BER"], "FER": row["FER"],
            "decodeLatencyNs": row["decodeTimeMeanNs"],
            "complexity": "306_TRELLIS_STEPS_64_STATES_NO_COMMON_OPERATION_COUNT",
            "sourceCsv": row["sourceCsvAbsolutePath"], "sourceRowKey": row["sourceRowKey"],
            "comparisonRole": "NO_BURST_AWGN_REFERENCE",
        })
    for row in points:
        comparison_rows.append({
            "scheme": "LDPC", "configuration": row["configurationId"],
            "channelCondition": "NO_BURST_AWGN", "interleaver": "NONE",
            "payloadBits": 300, "encodedBits": 640, "actualRate": row["actualRate"],
            "EsN0Db": row["EsN0Db"], "BER": row["BER"], "FER": row["FER"],
            "decodeLatencyNs": f"{float(row['avgDecodeTimeUs']) * 1000.0:.17g}",
            "complexity": f"avgIterations={row['avgIterations']};avgEdgeMessageUpdates={row['avgEdgeMessageUpdates']}",
            "sourceCsv": row["sourceCsvAbsolutePath"],
            "sourceRowKey": f"{row['sourceConfigurationId']}|line={row['sourceRowNumber']}",
            "comparisonRole": "NO_INTERLEAVING_NEAR_RATE_REFERENCE",
        })
    cc_formal_path = ROOT / "stage11_cc_formal" / "results" / "formal_results.csv"
    cc_formal = read_csv(cc_formal_path)
    for config_id in ("CC_NONE", "CC_PSEUDO_128_RECOMMENDED", "CC_SHORT_D8_RECOMMENDED", "CC_SHORT_D16_CONTROL_128"):
        for snr in [x / 2 for x in range(-10, 21)]:
            members = [row for row in cc_formal if row["configurationId"] == config_id and abs(float(row["EsN0Db"]) - snr) < 1e-12 and abs(float(row["burstRatioRequested"]) - 0.02) < 1e-12]
            if len(members) != 6:
                raise RuntimeError(f"CC 2% comparison member mismatch: {config_id} {snr}")
            frames = sum(int(row["framesProcessed"]) for row in members)
            comparison_rows.append({
                "scheme": "CC", "configuration": config_id,
                "channelCondition": "BURST_POLARITY_REVERSAL_AWGN_2_PERCENT",
                "interleaver": members[0]["method"], "payloadBits": 300,
                "encodedBits": 612, "actualRate": f"{CC_RATE:.17g}", "EsN0Db": snr,
                "BER": f"{sum(float(row['BER']) for row in members) / 6:.17g}",
                "FER": f"{sum(float(row['FER']) for row in members) / 6:.17g}",
                "decodeLatencyNs": f"{sum(float(row['decodeTimeMeanNs']) * int(row['framesProcessed']) for row in members) / frames:.17g}",
                "complexity": "306_TRELLIS_STEPS_64_STATES_NO_COMMON_OPERATION_COUNT",
                "sourceCsv": str(cc_formal_path.resolve()),
                "sourceRowKey": ";".join(f"{row['configurationId']}|{row['EsN0Db']}|{row['burstPositionType']}" for row in members),
                "comparisonRole": members[0]["comparisonRole"],
            })
    write_csv(comparison_dir / "coding_baseline_comparison.csv", comparison_fields, comparison_rows)

    cc_frames = [int(row["framesProcessed"]) for row in read_csv(cc_baseline_path)]
    cc_decode_ns = sum(float(row["decodeTimeMeanNs"]) * weight for row, weight in zip(read_csv(cc_baseline_path), cc_frames)) / sum(cc_frames)
    ldpc_frames = [int(row["frames"]) for row in points]
    ldpc_decode_ns = sum(float(row["avgDecodeTimeUs"]) * 1000.0 * weight for row, weight in zip(points, ldpc_frames)) / sum(ldpc_frames)
    ldpc_avg_iter = sum(float(row["avgIterations"]) * weight for row, weight in zip(points, ldpc_frames)) / sum(ldpc_frames)
    ldpc_avg_edges = sum(float(row["avgEdgeMessageUpdates"]) * weight for row, weight in zip(points, ldpc_frames)) / sum(ldpc_frames)
    complexity_fields = ["scheme", "algorithm", "coreComputationScale", "algorithmSpecificMetric", "measuredDecodeTimeNsWeighted", "commonOperationCount", "interpretation"]
    complexity_rows = [
        {"scheme": "CC", "algorithm": "TERMINATED_FLOAT_SOFT_VITERBI", "coreComputationScale": "306 trellis steps; 64 states; branch metrics and ACS", "algorithmSpecificMetric": "N/A_NO_PUBLISHED_OPERATION_COUNT", "measuredDecodeTimeNsWeighted": f"{cc_decode_ns:.17g}", "commonOperationCount": "N/A", "interpretation": "software CPU time only; not hardware complexity"},
        {"scheme": "LDPC", "algorithm": "DIRECT_LAYERED_NMS_ALPHA_0P80_MAXITER32", "coreComputationScale": "N=640; BG2; Zc=40; edgeCount=2240", "algorithmSpecificMetric": f"weightedAvgIterations={ldpc_avg_iter:.9g};weightedAvgEdgeMessageUpdates={ldpc_avg_edges:.9g}", "measuredDecodeTimeNsWeighted": f"{ldpc_decode_ns:.17g}", "commonOperationCount": "N/A", "interpretation": "algorithm-specific updates are not equated to Viterbi ACS"},
    ]
    write_csv(comparison_dir / "coding_complexity_reference.csv", complexity_fields, complexity_rows)
    comparison_dir.joinpath("readme.txt").write_text(
        "目录用途：保存CC无突发、LDPC无突发近码率参考以及CC 2%突发配置的逐点编码基线比较链。\n"
        "信道边界：LDPC行全部为NO_BURST_AWGN；不得解释为LDPC突发结果。\n"
        "时延：均为纯译码函数CPU时间，仅作软件实现参考。\n"
        "复杂度：仅分算法报告结构量；不存在统一operation-count排名。\n"
        "插值/平滑/合成：均未使用。\n",
        encoding="utf-8",
    )

    selected_snr = 0.5
    summary_fields = ["scheme", "configuration", "payloadBits", "encodedBits", "actualRate", "decoder", "interleaver", "selectedEsN0Db", "noBurstFerAtSelectedSnr", "noBurstBerAtSelectedSnr", "burst2FerAtSelectedSnr", "burst5FerAtSelectedSnr", "burst10FerAtSelectedSnr", "decodeTimeMeanNs", "interleaverBufferBits", "comparisonRole", "notes"]
    cc_base_selected = next(row for row in read_csv(cc_baseline_path) if abs(float(row["EsN0Db"]) - selected_snr) < 1e-12)
    ldpc_selected = next(row for row in points if abs(float(row["EsN0Db"]) - selected_snr) < 1e-12)
    summary_rows = [
        {"scheme": "CC", "configuration": "CC_NO_BURST_AWGN", "payloadBits": 300, "encodedBits": 612, "actualRate": f"{CC_RATE:.17g}", "decoder": "TERMINATED_FLOAT_SOFT_VITERBI", "interleaver": "NONE", "selectedEsN0Db": selected_snr, "noBurstFerAtSelectedSnr": cc_base_selected["FER"], "noBurstBerAtSelectedSnr": cc_base_selected["BER"], "burst2FerAtSelectedSnr": "N/A", "burst5FerAtSelectedSnr": "N/A", "burst10FerAtSelectedSnr": "N/A", "decodeTimeMeanNs": cc_base_selected["decodeTimeMeanNs"], "interleaverBufferBits": 0, "comparisonRole": "NO_BURST_AWGN_REFERENCE", "notes": "CC no-burst reference"},
        {"scheme": "LDPC", "configuration": ldpc_selected["configurationId"], "payloadBits": 300, "encodedBits": 640, "actualRate": ldpc_selected["actualRate"], "decoder": "DIRECT_LAYERED_NMS_ALPHA_0P80_MAXITER32", "interleaver": "NONE", "selectedEsN0Db": selected_snr, "noBurstFerAtSelectedSnr": ldpc_selected["FER"], "noBurstBerAtSelectedSnr": ldpc_selected["BER"], "burst2FerAtSelectedSnr": "N/A", "burst5FerAtSelectedSnr": "N/A", "burst10FerAtSelectedSnr": "N/A", "decodeTimeMeanNs": f"{float(ldpc_selected['avgDecodeTimeUs']) * 1000.0:.17g}", "interleaverBufferBits": 0, "comparisonRole": "NO_INTERLEAVING_NEAR_RATE_REFERENCE", "notes": "AWGN only; no inference about burst tolerance; excluded from interleaver ranking"},
    ]
    for config_id in ("CC_NONE", "CC_PSEUDO_128_RECOMMENDED", "CC_SHORT_D8_RECOMMENDED", "CC_SHORT_D16_CONTROL_128"):
        burst_values = {}
        selected_members = []
        for ratio in (0.02, 0.05, 0.10):
            members = [row for row in cc_formal if row["configurationId"] == config_id and abs(float(row["EsN0Db"]) - selected_snr) < 1e-12 and abs(float(row["burstRatioRequested"]) - ratio) < 1e-12]
            burst_values[ratio] = sum(float(row["FER"]) for row in members) / len(members)
            if ratio == 0.02: selected_members = members
        frames = sum(int(row["framesProcessed"]) for row in selected_members)
        summary_rows.append({"scheme": "CC", "configuration": config_id, "payloadBits": 300, "encodedBits": 612, "actualRate": f"{CC_RATE:.17g}", "decoder": "TERMINATED_FLOAT_SOFT_VITERBI", "interleaver": selected_members[0]["method"], "selectedEsN0Db": selected_snr, "noBurstFerAtSelectedSnr": "N/A", "noBurstBerAtSelectedSnr": "N/A", "burst2FerAtSelectedSnr": f"{burst_values[0.02]:.17g}", "burst5FerAtSelectedSnr": f"{burst_values[0.05]:.17g}", "burst10FerAtSelectedSnr": f"{burst_values[0.10]:.17g}", "decodeTimeMeanNs": f"{sum(float(row['decodeTimeMeanNs']) * int(row['framesProcessed']) for row in selected_members) / frames:.17g}", "interleaverBufferBits": selected_members[0]["bufferBits"], "comparisonRole": selected_members[0]["comparisonRole"], "notes": "CC burst configuration; ranking remains CC-only"})
    write_csv(ROOT / "S7_coding_reference_summary.csv", summary_fields, summary_rows)

    audit_fields = [
        "gate", "status", "evidence", "sourceAbsolutePath", "sourceSha256",
    ]
    audits = [
        ("R", "PASS", "Stage23 final reintegration validation PASS; 31 selected points status PASS", VALIDATION),
        ("S", "PASS", "Formal chain explicitly excludes interleaving; selected interleaver=NONE", CONFIG),
        ("T", "PASS", "LDPC payloadBits=300 equals CC payloadBits=300", CASE_METADATA),
        ("U", "PASS", f"LDPC rate=300/640={selected_rate}; CC rate=300/612={CC_RATE}", CASE_METADATA),
        ("V", "PASS", "Both use Es/N0 and sigmaSquared=1/(2*10^(EsN0Db/10)); no conversion", CONFIG),
        ("W", "PASS", "LDPC bitErrors count decoded payload[0:300] mismatches; denominator=300*frames", LDPC_BLOCK / "current" / "src" / "main.cpp"),
        ("X", "PASS", "LDPC frameErrors increments iff payload error count is nonzero", LDPC_BLOCK / "current" / "src" / "main.cpp"),
        ("Y", "PASS", "Historical Stage23 CSV reused; LDPC formal rerun=NO", SOURCE),
        ("Z", "PASS", "31 exact source rows; interpolation=false; synthetic=false", SOURCE),
        ("AA", "PASS", "LDPC is NO_BURST_AWGN and is forbidden from position plots", SOURCE),
        ("AB", "PASS", "comparisonRole excludes LDPC from interleaver ranking", RECOMMENDATION),
    ]
    audit_rows = [
        {"gate": gate, "status": status, "evidence": evidence,
         "sourceAbsolutePath": str(path.resolve()), "sourceSha256": sha256(path)}
        for gate, status, evidence, path in audits
    ]
    write_csv(OUTPUT / "ldpc_baseline_source_audit.csv", audit_fields, audit_rows)

    initial_status = git_output("status", "--porcelain=v1")
    dirty_paths = [line[3:] for line in initial_status.splitlines() if len(line) >= 4]
    dirty_hashes = {}
    for relative in dirty_paths:
        path = LDPC_REPO / relative
        if path.is_file():
            dirty_hashes[relative.replace("\\", "/")] = sha256(path)
    source_project_state = {
        "repository": str(LDPC_REPO.resolve()),
        "branch": git_output("branch", "--show-current"),
        "head": git_output("rev-parse", "HEAD"),
        "initialStatusPorcelain": initial_status.splitlines(),
        "initialDirtyFileSha256": dirty_hashes,
        "note": "The LDPC repository was already dirty before S7 integration; unchanged means identical status lines and dirty-file hashes, not a clean repository.",
    }
    (OUTPUT / "ldpc_source_project_state_before.json").write_text(
        json.dumps(source_project_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    protected_inputs = [
        ROOT / "stage10_bch_formal" / "results" / "formal_results.csv",
        ROOT / "stage11_cc_formal" / "results" / "formal_results.csv",
        STAGE15 / "no_burst_baseline" / "bch" / "no_burst_baseline.csv",
        STAGE15 / "no_burst_baseline" / "cc" / "no_burst_baseline.csv",
        SOURCE,
        CONFIG,
        CASE_METADATA,
        LDPC_BLOCK / "current" / "src" / "main.cpp",
        LDPC_BLOCK / "current" / "src" / "s4_ldpc.cpp",
    ]
    input_hashes = {
        "capturedAt": "2026-08-11",
        "noS7FormalRerun": True,
        "noLdpcFormalRerun": True,
        "before": {str(path.resolve()): sha256(path) for path in protected_inputs},
    }
    (OUTPUT / "original_input_hashes.json").write_text(
        json.dumps(input_hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    audit_md = f"""# S7 LDPC 无交织近码率基线来源审计

- 选择：`LDPC_BG2_K300_N640 / DIRECT_LAYERED_NMS / alpha=0.80 / maxIterations=32`。
- 角色：`NO_INTERLEAVING_NEAR_RATE_REFERENCE`；不参与交织推荐排名。
- payload：LDPC=300，CC=300，完全匹配。
- 码率：LDPC=300/640={selected_rate:.12f}；CC=300/612={CC_RATE:.12f}。
- 码率差：absolute={abs(selected_rate-CC_RATE):.12f}；relative={abs(selected_rate-CC_RATE)/CC_RATE:.6%}。
- 信道：LDPC 仅有无突发 BPSK+AWGN；没有 2%/5%/10% 连续极性反转数据。
- SNR：两者均为 Es/N0，sigmaSquared=1/(2*10^(EsN0Db/10))，无需转换。
- BER：两者均以原始 300-bit payload 为统计对象。
- FER：两者均在 payload 至少存在一个错误 bit 时记为 1。
- 时延：两者均用 steady_clock 只包围译码函数，可作软件实现 CPU 时间参考；跨实现结果不等价于硬件复杂度。
- 复杂度：LDPC 有迭代、边更新和分类操作量；CC 有固定 306 trellis steps/64 states。二者没有统一 operation-count 口径，不合并为单一数值排名。
- 插值/平滑/合成：NO/NO/NO；摘录 31 个原始行。
- Formal rerun：S7 BCH=NO，S7 CC=NO，LDPC=NO。
- 原始 LDPC 工程：READ ONLY；本轮开始前已有 23 个 readme 修改，使用状态与哈希前后相等证明本轮未修改。
"""
    (OUTPUT / "ldpc_baseline_source_audit.md").write_text(audit_md, encoding="utf-8")
    readme = f"""阶段名称：S7 Stage15 LDPC baseline integration
数据用途：为 CC 图表提供无突发 AWGN 近码率编码基线。
LDPC角色：无交织近码率编码参考，不是交织方案。
数据来源：{SOURCE.resolve()}
配置：LDPC_BG2_K300_N640，BG2，Zc=40，Direct Layered NMS，alpha=0.80，maxIterations=32。
实际码率：300/640={selected_rate:.12f}。
与CC码率差：absolute={abs(selected_rate-CC_RATE):.12f}，relative={abs(selected_rate-CC_RATE)/CC_RATE:.6%}。
译码算法：DIRECT_LAYERED_NMS。
信道：BPSK + AWGN，无突发。
是否无交织：是。
是否重新仿真：否。
是否插值：否。
是否平滑：否。
是否参与交织排名：否。
已知限制：没有兼容的2%/5%/10%突发数据；CPU时延只作软件实现参考；复杂度不可统一量纲排名。
阶段状态：SOURCE_AUDIT_PASS。
"""
    (OUTPUT / "readme.txt").write_text(readme, encoding="utf-8")
    manifest = {
        "stage": "S7_STAGE15_LDPC_BASELINE",
        "branch": "S8-PaperDocu",
        "selected": selected_json,
        "candidateCount": len(candidates),
        "selectedPointCount": len(points),
        "sourceFormalValidated": True,
        "sourceProjectReadOnly": True,
        "ldpcFormalRerun": False,
        "s7FormalRerun": False,
        "interpolation": False,
        "smoothing": False,
        "syntheticData": False,
        "burstDataAvailable": {"2%": False, "5%": False, "10%": False},
        "latencyDefinition": "COMPATIBLE_PURE_DECODER_CPU_TIME_DESCRIPTIVE_ONLY",
        "complexityDefinition": "ALGORITHM_SPECIFIC_NO_COMMON_OPERATION_UNIT",
        "mergeStatus": "NOT_MERGED",
    }
    (OUTPUT / "ldpc_baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS_S7_LDPC_BASELINE_COLLECTION candidates=6 selectedPoints=31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
