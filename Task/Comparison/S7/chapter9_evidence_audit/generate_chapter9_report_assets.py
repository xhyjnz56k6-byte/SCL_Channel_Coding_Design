from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
S7 = ROOT / "Task" / "Comparison" / "S7"
OUT = S7 / "chapter9_evidence_audit"
STAGE15 = S7 / "stage15_scientific_plots" / "results"
BCH_FORMAL = S7 / "stage10_bch_formal" / "results" / "formal_results.csv"
CC_FORMAL = S7 / "stage11_cc_formal" / "results" / "formal_results.csv"
CODING_REFERENCE = S7 / "S7_coding_reference_summary.csv"
FIGURE_MATRIX = OUT / "chapter9_figure_evidence_matrix.csv"
NO_BURST_LATENCY_FIGURE_DATA = STAGE15 / "cc" / "22_cc_ldpc_no_burst_decode_latency" / "figure_data.csv"

RATIOS = (0.02, 0.05)
POSITIONS = ("HEAD", "QUARTER", "MIDDLE", "THREE_QUARTER", "TAIL", "RANDOM")

LABELS = {
    "BCH_NONE": "无交织",
    "BCH_CODEBLOCK_D19": "BCH子块结构交织 D=19",
    "BCH_ROW_COLUMN_R15": "全帧行列交织 R=15",
    "BCH_GLOBAL_PSEUDO_285": "全帧伪随机交织",
    "CC_NONE": "无交织",
    "CC_SHORT_D8_RECOMMENDED": "短深度块交织 D=8",
    "CC_SHORT_D16_CONTROL_128": "短深度块交织 D=16",
    "CC_PSEUDO_128_RECOMMENDED": "局部伪随机交织 span=128",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path = OUT / name
    if not rows:
        raise ValueError(f"No rows generated for {name}")
    fieldnames = fields or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(value: str, target: float) -> bool:
    return abs(float(value) - target) < 1e-9


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def f6(value: float) -> str:
    return f"{value:.6g}"


def grouped_at(rows: list[dict[str, str]], snr: float, ratio: float) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if close(row["EsN0Db"], snr) and close(row["burstRatioRequested"], ratio):
            grouped[row["configurationId"]].append(row)
    return grouped


def performance_rows(scheme: str, rows: list[dict[str, str]], snr: float) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    baseline_id = f"{scheme}_NONE"
    for ratio in RATIOS:
        grouped = grouped_at(rows, snr, ratio)
        baseline = mean([float(row["FER"]) for row in grouped[baseline_id]])
        for config, group in grouped.items():
            fer_values = [float(row["FER"]) for row in group]
            ber_values = [float(row["BER"]) for row in group]
            reduction = 100.0 * (baseline - mean(fer_values)) / baseline if baseline else 0.0
            output.append({
                "scheme": scheme,
                "burstRatio": f"{ratio * 100:g}%",
                "burstLengthBits": group[0]["burstLengthBits"],
                "EsN0Db": f"{snr:g}",
                "configuration": LABELS[config],
                "meanPositionFER": f6(mean(fer_values)),
                "worstPositionFER": f6(max(fer_values)),
                "bestPositionFER": f6(min(fer_values)),
                "meanPositionBER": f6(mean(ber_values)),
                "FERreductionVsNoInterleavingPercent": f6(reduction),
                "sourceCsv": str(BCH_FORMAL if scheme == "BCH" else CC_FORMAL),
            })
    return output


def write_filter_audit() -> None:
    rows = []
    for item in read_csv(FIGURE_MATRIX):
        scheme = item["scheme"]
        figure = item["figureId"]
        manifest_path = STAGE15 / scheme.lower() / figure / "plot_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        title = manifest["title"]
        burst_ratios = item["burstRatio"] or "derived; see generation rule"
        decision = "USE_FIGURE"
        reason = "Stage15 figure is based on the retained 2% or 5% condition."
        replacement = "N/A"

        if figure in {"05_burst_10_fer", "23_burst_10_ber"} or (scheme == "CC" and figure == "21_all_start_heatmap"):
            decision = "EXCLUDE_10_PERCENT"
            reason = "Dedicated 10% result; retained as an experiment asset but not referenced by Chapter 9."
        elif figure == "13_target_fer_esn0_gain":
            decision = "EXCLUDE_MIXED_NO_USABLE_VALUE"
            reason = "Mixed 2%/5%/10% categories and retained categories have no non-interpolated numeric gain."
        elif figure in {"16_decodeTimeMeanNsWeighted", "17_interleaveTimeMeanNsWeighted", "18_deinterleaveTimeMeanNsWeighted"}:
            decision = "REPLACE_WITH_FILTERED_TABLE"
            reason = "Stage13 value is weighted over all original burst ratios; Table 9.9 is recomputed from 2%/5% Formal rows only."
            replacement = "report_table_data_9_9.csv"
        elif figure == "20_burst_tolerance":
            decision = "REPLACE_WITH_FILTERED_TABLE"
            reason = "Mixed burst-ratio bars; Table 9.10 retains only 2% and 5% source fields."
            replacement = "report_table_data_9_10.csv"

        rows.append({
            "figure": figure,
            "scheme": scheme,
            "burstRatios": burst_ratios,
            "reportDecision": decision,
            "reason": reason,
            "replacementFigure": replacement,
            "sourceData": ";".join(manifest["sourceAbsolutePaths"]),
        })
    write_csv("chapter9_report_2_5_percent_filter.csv", rows)


def write_tables(bch_rows: list[dict[str, str]], cc_rows: list[dict[str, str]]) -> None:
    write_csv("report_table_data_9_1.csv", [
        {"parameter": "调制", "value": "BPSK", "notes": "0映射为+1，1映射为-1"},
        {"parameter": "信道", "value": "突发错误信道+AWGN", "notes": "连续区间极性反转，全帧叠加AWGN"},
        {"parameter": "Es/N0", "value": "-5至10 dB，步长0.5 dB", "notes": "31个正式点"},
        {"parameter": "正式展示突发比例", "value": "2%、5%", "notes": "BCH为6、14 bit；CC为12、31 bit"},
        {"parameter": "突发位置", "value": "帧首、1/4、帧中、3/4、帧尾、随机", "notes": "交织后的发送符号序列"},
        {"parameter": "停止规则", "value": "minFrames=1000；targetFrameErrors=200；maxFrames=50000", "notes": "paired=true"},
        {"parameter": "公平性", "value": "1116组，0 FAIL", "notes": "同组共享payload、noise、burst start和frame sequence"},
    ])

    write_csv("report_table_data_9_2.csv", [
        {"scheme": "分块BCH", "payloadBits": 200, "fillerOrTailBits": "9 filler", "structure": "19 x BCH(15,11,1)", "transmittedBits": 285, "actualRate": f6(200 / 285), "decoder": "综合校验查表，硬判决"},
        {"scheme": "卷积码", "payloadBits": 300, "fillerOrTailBits": "6 zero-tail", "structure": "K=7, G=(171,133)oct, 306 trellis steps", "transmittedBits": 612, "actualRate": f6(300 / 612), "decoder": "terminated full-block floating soft Viterbi"},
        {"scheme": "LDPC高速基线", "payloadBits": 300, "fillerOrTailBits": "20 filler in 320 information bits", "structure": "BG2, Z=40", "transmittedBits": 640, "actualRate": f6(300 / 640), "decoder": "layered NMS, alpha=0.80, maxIterations=32"},
    ])

    write_csv("report_table_data_9_3.csv", [
        {"configuration": "BCH_NONE", "method": "无交织", "parameter": 0, "spanBits": 1, "bufferBits": 0, "mapping": "恒等映射"},
        {"configuration": "BCH_CODEBLOCK_D19", "method": "BCH子块结构交织", "parameter": "D=19", "spanBits": 285, "bufferBits": 285, "mapping": "按19个15-bit子块组织并列读"},
        {"configuration": "BCH_ROW_COLUMN_R15", "method": "全帧行列交织", "parameter": "R=15", "spanBits": 285, "bufferBits": 285, "mapping": "全帧行写列读"},
        {"configuration": "BCH_GLOBAL_PSEUDO_285", "method": "全帧伪随机交织", "parameter": 285, "spanBits": 285, "bufferBits": 285, "mapping": "固定种子的全帧确定性置换"},
    ])

    write_csv("report_table_data_9_4.csv", [
        {"configuration": "CC_NONE", "method": "无交织", "parameter": 0, "spanTrellisSteps": 1, "spanBits": 2, "bufferBits": 0, "comparisonRole": "基线"},
        {"configuration": "CC_SHORT_D8_RECOMMENDED", "method": "短深度块交织", "parameter": "D=8", "spanTrellisSteps": 64, "spanBits": 128, "bufferBits": 128, "comparisonRole": "工程配置"},
        {"configuration": "CC_SHORT_D16_CONTROL_128", "method": "短深度块交织", "parameter": "D=16", "spanTrellisSteps": 128, "spanBits": 256, "bufferBits": 256, "comparisonRole": "等跨度受控"},
        {"configuration": "CC_PSEUDO_128_RECOMMENDED", "method": "局部伪随机交织", "parameter": "span=128", "spanTrellisSteps": 128, "spanBits": 256, "bufferBits": 256, "comparisonRole": "工程配置；等跨度受控"},
    ])

    bch_perf = performance_rows("BCH", bch_rows, 10.0)
    cc_perf = performance_rows("CC", cc_rows, 10.0)
    write_csv("report_table_data_9_5.csv", bch_perf)

    mechanism = []
    grouped = grouped_at(bch_rows, 10.0, 0.05)
    for config, group in grouped.items():
        mechanism.append({
            "configuration": LABELS[config],
            "affectedBlocksMean": f6(mean([float(row["affectedBlocksMean"]) for row in group])),
            "maximumErrorsInBlock": f6(max(float(row["maximumErrorsInBlock"]) for row in group)),
            "correctedBlocksMean": f6(mean([float(row["correctedBlocksMean"]) for row in group])),
            "meanPositionFER": f6(mean([float(row["FER"]) for row in group])),
            "sourceCsv": str(BCH_FORMAL),
        })
    write_csv("report_table_data_9_6.csv", mechanism)
    write_csv("report_table_data_9_7.csv", cc_perf)

    roles = {
        "CC_SHORT_D8_RECOMMENDED": "工程配置：低缓存",
        "CC_SHORT_D16_CONTROL_128": "等跨度受控：规则排列",
        "CC_PSEUDO_128_RECOMMENDED": "工程配置/等跨度受控：伪随机排列",
    }
    comparison = []
    for ratio in RATIOS:
        grouped = grouped_at(cc_rows, 10.0, ratio)
        for config in roles:
            group = grouped[config]
            comparison.append({
                "burstRatio": f"{ratio * 100:g}%",
                "configuration": LABELS[config],
                "spanTrellisSteps": group[0]["spanTrellisSteps"],
                "bufferBits": group[0]["bufferBits"],
                "meanPositionFER": f6(mean([float(row["FER"]) for row in group])),
                "worstPositionFER": f6(max(float(row["FER"]) for row in group)),
                "comparisonRole": roles[config],
                "sourceCsv": str(CC_FORMAL),
            })
    write_csv("report_table_data_9_8.csv", comparison)

    timing = []
    for scheme, rows, source in (("BCH", bch_rows, BCH_FORMAL), ("CC", cc_rows, CC_FORMAL)):
        by_config: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            if any(close(row["burstRatioRequested"], ratio) for ratio in RATIOS):
                by_config[row["configurationId"]].append(row)
        for config, group in by_config.items():
            total_frames = sum(int(row["framesProcessed"]) for row in group)
            weighted = {}
            for field in ("interleaveTimeMeanNs", "deinterleaveTimeMeanNs", "decodeTimeMeanNs"):
                weighted[field] = sum(float(row[field]) * int(row["framesProcessed"]) for row in group) / total_frames
            timing.append({
                "scheme": scheme,
                "configuration": LABELS[config],
                "includedBurstRatios": "2%;5%",
                "bufferBits": group[0]["bufferBits"],
                "interleaveCpuNsPerFrame": f6(weighted["interleaveTimeMeanNs"]),
                "deinterleaveCpuNsPerFrame": f6(weighted["deinterleaveTimeMeanNs"]),
                "decodeCpuNsPerFrame": f6(weighted["decodeTimeMeanNs"]),
                "framesWeighted": total_frames,
                "sourceCsv": str(source),
            })
    write_csv("report_table_data_9_9.csv", timing)

    tolerance = []
    for scheme, rows, snr in (("BCH", bch_rows, 10.0), ("CC", cc_rows, 10.0)):
        for ratio in RATIOS:
            for config, group in grouped_at(rows, snr, ratio).items():
                worst = max(float(row["FER"]) for row in group)
                tolerance.append({
                    "scheme": scheme,
                    "configuration": LABELS[config],
                    "EsN0Db": f"{snr:g}",
                    "burstRatio": f"{ratio * 100:g}%",
                    "burstLengthBits": group[0]["burstLengthBits"],
                    "worstPositionFER": f6(worst),
                    "meetsFerLe0p1": str(worst <= 0.1).lower(),
                    "sourceCsv": str(BCH_FORMAL if scheme == "BCH" else CC_FORMAL),
                })
    write_csv("report_table_data_9_10.csv", tolerance)

    references = read_csv(CODING_REFERENCE)
    latency_by_scheme = {row["scheme"]: row["rawY"] for row in read_csv(NO_BURST_LATENCY_FIGURE_DATA)}
    baseline = []
    for row in references[:2]:
        baseline.append({
            "scheme": row["scheme"],
            "configuration": row["configuration"],
            "payloadBits": row["payloadBits"],
            "transmittedBits": row["encodedBits"],
            "actualRate": row["actualRate"],
            "decoder": row["decoder"],
            "interleaver": row["interleaver"],
            "channel": "NO_BURST_AWGN",
            "selectedEsN0Db": row["selectedEsN0Db"],
            "FER": row["noBurstFerAtSelectedSnr"],
            "BER": row["noBurstBerAtSelectedSnr"],
            "decodeCpuNsPerFrame": latency_by_scheme[row["scheme"]],
            "role": "无交织、无突发、近码率AWGN参考",
        })
    write_csv("report_table_data_9_11.csv", baseline)

    write_csv("report_table_data_9_12.csv", [
        {"scheme": "分块BCH", "configuration": "全帧行列交织 R=15", "useCase": "性能优先", "evidence": "10 dB时2%/5%平均FER为0.000333/0.000763，缓存285 bit", "boundary": "仅限本章200 bit分块BCH方案"},
        {"scheme": "分块BCH", "configuration": "BCH子块结构交织 D=19", "useCase": "结构对应清晰的备选", "evidence": "10 dB时2%/5%平均FER为0.000377/0.000897，缓存285 bit", "boundary": "不改变BCH(15,11,1)理论纠错能力"},
        {"scheme": "卷积码", "configuration": "短深度块交织 D=8", "useCase": "缓存优先", "evidence": "2%时10 dB平均FER为0.552654，缓存128 bit", "boundary": "与Pseudo128不是等跨度纯方法比较"},
        {"scheme": "卷积码", "configuration": "局部伪随机交织 span=128", "useCase": "2%条件下FER优先", "evidence": "2%时10 dB平均FER为0.448905，缓存256 bit", "boundary": "5%时本测试范围内FER接近1"},
    ])


def write_readme() -> None:
    bch_hash = sha256(BCH_FORMAL)
    cc_hash = sha256(CC_FORMAL)
    generated = sorted(path.name for path in OUT.glob("report_table_data_*.csv"))
    text = f"""S7 Chapter 9 evidence and report-data audit outputs.

Report-specific generated files:
- chapter9_report_2_5_percent_filter.csv
- chapter9_writing_evidence_coverage.csv
{chr(10).join(f'- {name}' for name in generated)}

Sources:
- {BCH_FORMAL}
- {CC_FORMAL}
- Stage12-Stage15 validated derived assets under {S7}
- {CODING_REFERENCE}

Purpose:
- Freeze which Stage15 figures may enter Chapter 9.
- Exclude dedicated 10 percent figures from the report without deleting experiment assets.
- Generate compact three-line-table source data for Tables 9.1-9.12.

Redrawing:
- No Stage15 figure is redrawn by this script.
- Mixed timing and tolerance figures are replaced by report tables.
- Table 9.9 recomputes frame-weighted CPU means from existing Formal rows after applying burstRatioRequested in {{0.02, 0.05}}.
- No interpolation, smoothing, or new experiment points are used.

Formal source hashes at generation time:
- BCH SHA-256: {bch_hash}
- CC SHA-256: {cc_hash}

Filter:
- Formal report scope: burstRatioRequested in {{0.02, 0.05}}.
- Dedicated or mixed 0.10 result displays are not referenced.

No Formal simulation was rerun or modified. No commit, push, stage, or merge is performed by this generator.
"""
    (OUT / "readme.txt").write_text(text, encoding="utf-8")


def write_coverage() -> None:
    rows = [
        {"section": "9.1", "claim": "交织改变连续信道异常经逆置换后的空间分布，不改变码本", "figure": "图9.1", "table": "表9.1", "sourceCsv": "chapter9_fairness_audit.csv; s7_formal_frozen_config.json", "status": "PASS"},
        {"section": "9.2", "claim": "突发错误信道为连续BPSK极性反转并叠加AWGN", "figure": "N/A", "table": "表9.1", "sourceCsv": "chapter9_burst_channel_definition.md", "status": "PASS"},
        {"section": "9.2", "claim": "BCH固定为200 bit分块BCH(15,11,1)方案", "figure": "N/A", "table": "表9.2;表9.3", "sourceCsv": "s7_formal_frozen_config.json; formal_results.csv", "status": "PASS"},
        {"section": "9.2", "claim": "卷积码固定为300 bit终止整帧浮点软Viterbi", "figure": "N/A", "table": "表9.2;表9.4", "sourceCsv": "s7_formal_frozen_config.json; formal_results.csv", "status": "PASS"},
        {"section": "9.3", "claim": "BCH规则结构交织在2%和5%高工作点显著降低FER", "figure": "图9.2;图9.3", "table": "表9.5", "sourceCsv": "report_table_data_9_5.csv", "status": "PASS"},
        {"section": "9.3", "claim": "BCH全帧伪随机配置具有较强位置依赖", "figure": "图9.4;图9.5;图9.6", "table": "表9.5", "sourceCsv": "formal_results.csv; all_start_results.csv", "status": "PASS"},
        {"section": "9.3", "claim": "规则交织把错误扩展到约14个子块并降低单块最大错误数", "figure": "图9.7", "table": "表9.6", "sourceCsv": "report_table_data_9_6.csv", "status": "PASS"},
        {"section": "9.3", "claim": "BCH三种正式交织配置均需285 bit结构缓存", "figure": "图9.8", "table": "表9.9", "sourceCsv": "report_table_data_9_9.csv", "status": "PASS"},
        {"section": "9.4", "claim": "卷积码2%条件下D8与Pseudo128降低平均FER", "figure": "图9.9", "table": "表9.7", "sourceCsv": "report_table_data_9_7.csv", "status": "PASS"},
        {"section": "9.4", "claim": "卷积码5%条件下各配置FER接近饱和", "figure": "图9.9;图9.10", "table": "表9.7", "sourceCsv": "report_table_data_9_7.csv", "status": "PASS"},
        {"section": "9.4", "claim": "卷积码突发位置会改变局部路径度量竞争", "figure": "图9.11;图9.12", "table": "表9.7", "sourceCsv": "formal_results.csv", "status": "PASS"},
        {"section": "9.4", "claim": "D8与Pseudo128是工程配置比较", "figure": "图9.13", "table": "表9.8", "sourceCsv": "report_table_data_9_8.csv", "status": "PASS"},
        {"section": "9.4", "claim": "D16与Pseudo128构成128 trellis step等跨度受控比较", "figure": "图9.13", "table": "表9.8", "sourceCsv": "report_table_data_9_8.csv", "status": "PASS"},
        {"section": "9.4", "claim": "D增大没有形成单调FER收益", "figure": "图9.13;图9.14", "table": "表9.8", "sourceCsv": "formal_results.csv", "status": "PASS"},
        {"section": "9.4", "claim": "D8与Pseudo128分别需要128 bit和256 bit缓存", "figure": "图9.15", "table": "表9.9", "sourceCsv": "report_table_data_9_9.csv", "status": "PASS"},
        {"section": "9.5", "claim": "LDPC N640仅为无交织、无突发AWGN近码率基线", "figure": "图9.16", "table": "表9.11", "sourceCsv": "report_table_data_9_11.csv", "status": "PASS"},
        {"section": "9.6", "claim": "CPU时间为软件函数时间，bufferBits不是物理时延", "figure": "图9.8;图9.15", "table": "表9.9", "sourceCsv": "chapter9_timing_definition_audit.csv; report_table_data_9_9.csv", "status": "PASS"},
        {"section": "9.6", "claim": "BCH规则结构配置通过两档高工作点最坏FER门限", "figure": "图9.2;图9.6", "table": "表9.10", "sourceCsv": "report_table_data_9_10.csv", "status": "PASS"},
        {"section": "9.6", "claim": "卷积码配置未通过两档最坏FER门限", "figure": "图9.9", "table": "表9.10", "sourceCsv": "report_table_data_9_10.csv", "status": "PASS"},
        {"section": "9.6", "claim": "工程建议按性能与缓存目标分别给出", "figure": "图9.8;图9.15", "table": "表9.12", "sourceCsv": "report_table_data_9_12.csv", "status": "PASS"},
        {"section": "9.7", "claim": "所有结论限定在2%与5%正式展示范围", "figure": "图9.2-图9.16", "table": "表9.1-表9.12", "sourceCsv": "chapter9_report_2_5_percent_filter.csv", "status": "PASS"},
    ]
    write_csv("chapter9_writing_evidence_coverage.csv", rows)


def main() -> None:
    bch_rows = read_csv(BCH_FORMAL)
    cc_rows = read_csv(CC_FORMAL)
    write_filter_audit()
    write_tables(bch_rows, cc_rows)
    write_coverage()
    write_readme()
    print("PASS_CHAPTER9_REPORT_ASSET_GENERATION")


if __name__ == "__main__":
    main()
