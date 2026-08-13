import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
OUTPUT = ROOT / "stage15_scientific_plots" / "no_burst_baseline"
BCH_SOURCE = REPO / "Task" / "BCH" / "simulation" / "stages" / "S1" / "stage07_awgn_dense_formal" / "published_results" / "stage07_awgn_dense_formal_results.csv"
CC_SOURCE = REPO / "Task" / "CC" / "simulation" / "stages" / "S3" / "stage09_awgn_formal" / "results" / "stage09_two_level_merged_point_results.csv"
FORMAL = {
    "BCH": ROOT / "stage10_bch_formal" / "results" / "formal_results.csv",
    "CC": ROOT / "stage11_cc_formal" / "results" / "formal_results.csv",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def write_csv(path, fields, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def normalize_bch():
    selected = [row for row in rows(BCH_SOURCE) if row["caseId"] == "K200_S15"]
    require(len(selected) == 37, "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: K200_S15 coverage")
    for row in selected:
        require(int(row["payloadLength"]) == 200, "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: payload")
        require((int(row["motherN"]), int(row["motherK"]), int(row["motherT"])) == (15, 11, 1), "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: component code")
        require(int(row["blockCount"]) == 19 and int(row["encodedLength"]) == 285, "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: organization")
        require(abs(float(row["actualRate"]) - 200.0 / 285.0) < 1e-15, "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: rate")
    output = []
    for row in selected:
        # Historical Stage07 stores sigma^2=10^(-snrDb/10).  S7 stores
        # sigma^2=0.5*10^(-EsN0Db/10), hence Es/N0=snrDb-10log10(2).
        esn0 = float(row["snrDb"]) - 10.0 * math.log10(2.0)
        if -5.0 <= esn0 <= 10.0:
            output.append({
                "scheme": "BCH", "configurationId": "NO_BURST_AWGN", "EsN0Db": f"{esn0:.17g}",
                "BER": row["ber"], "FER": row["fer"], "decodeTimeMeanNs": row["decodeTimeMeanNs"],
                "decodeTimeP95Ns": row["decodeTimeP95Ns"], "decodeTimeP99Ns": row["decodeTimeP99Ns"],
                "decodeTimeMaxNs": row["decodeTimeMaxNs"], "framesProcessed": row["totalFrames"],
                "sourceCsvAbsolutePath": str(BCH_SOURCE.resolve()), "sourceStage": "BCH_S1_stage07_awgn_dense_formal",
                "sourceConfigurationId": row["caseId"], "sourceRowKey": row["pointRunId"],
                "snrMapping": "EsN0Db=snrDb-10log10(2)", "interpolated": "false", "synthetic": "false",
            })
    require(output, "ERROR_NO_MATCHING_NO_BURST_BASELINE_BCH: no points in S7 display range")
    return output


def normalize_cc():
    candidates = [row for row in rows(CC_SOURCE) if row["caseId"] == "CC-B-R12-S"]
    selected = []
    for row in candidates:
        x = float(row["esN0Db"])
        on_s7_grid = -5.0 <= x <= 10.0 and abs(x * 2.0 - round(x * 2.0)) < 1e-10
        if on_s7_grid:
            selected.append(row)
    require(len(selected) == 31, "ERROR_NO_MATCHING_NO_BURST_BASELINE_CC: coarse S7 grid coverage")
    require(len({round(float(row["esN0Db"]), 10) for row in selected}) == 31, "ERROR_NO_MATCHING_NO_BURST_BASELINE_CC: duplicate SNR")
    for row in selected:
        require(int(row["N_transmitted"]) == 612, "ERROR_NO_MATCHING_NO_BURST_BASELINE_CC: encoded length")
        require(abs(float(row["actualRate"]) - 300.0 / 612.0) < 1e-15, "ERROR_NO_MATCHING_NO_BURST_BASELINE_CC: rate")
    return [{
        "scheme": "CC", "configurationId": "NO_BURST_AWGN", "EsN0Db": row["esN0Db"],
        "BER": row["BER"], "FER": row["FER"],
        "decodeTimeMeanNs": f"{1000.0 * float(row['avgDecodeTime_us']):.17g}",
        "decodeTimeP95Ns": f"{1000.0 * float(row['p95DecodeTime_us']):.17g}",
        "decodeTimeP99Ns": "", "decodeTimeMaxNs": f"{1000.0 * float(row['maxDecodeTime_us']):.17g}",
        "framesProcessed": row["framesProcessed"], "sourceCsvAbsolutePath": str(CC_SOURCE.resolve()),
        "sourceStage": "CC_S3_stage09_awgn_formal", "sourceConfigurationId": row["caseId"],
        "sourceRowKey": row["mergedRowId"], "snrMapping": "EsN0Db=esN0Db (identity)",
        "interpolated": "false", "synthetic": "false",
    } for row in sorted(selected, key=lambda value: float(value["esN0Db"]))]


def audit_rows(bch_points, cc_points):
    fields = ["scheme", "metric", "sourceCsvAbsolutePath", "sourceStage", "sourceConfigurationId", "payloadBits", "encodedBits", "codeRate", "decoder", "decision", "channel", "interleaver", "snrDefinition", "snrStart", "snrStop", "snrStep", "pointCount", "matchedToS7", "matchReason", "legacySource", "usedForPlot", "sha256"]
    common = []
    for metric in ("BER", "FER", "decodeTimeMeanNs"):
        common.append({"scheme": "BCH", "metric": metric, "sourceCsvAbsolutePath": str(BCH_SOURCE.resolve()), "sourceStage": "Task/BCH/simulation/S1/stage07_awgn_dense_formal", "sourceConfigurationId": "K200_S15", "payloadBits": 200, "encodedBits": 285, "codeRate": "200/285", "decoder": "SYNDROME_LOOKUP", "decision": "HARD", "channel": "BPSK_AWGN_NO_BURST", "interleaver": "NONE", "snrDefinition": "Es/N0 after documented Stage07 waveform-SNR conversion", "snrStart": min(float(x["EsN0Db"]) for x in bch_points), "snrStop": max(float(x["EsN0Db"]) for x in bch_points), "snrStep": 0.5, "pointCount": len(bch_points), "matchedToS7": "true", "matchReason": "Exact 200-bit segmented 19xBCH(15,11,1), 285 coded bits, hard syndrome lookup; sigma formula proves Es/N0 conversion", "legacySource": "true", "usedForPlot": "true", "sha256": digest(BCH_SOURCE)})
        common.append({"scheme": "CC", "metric": metric, "sourceCsvAbsolutePath": str(CC_SOURCE.resolve()), "sourceStage": "Task/CC/simulation/S3/stage09_awgn_formal", "sourceConfigurationId": "CC-B-R12-S", "payloadBits": 300, "encodedBits": 612, "codeRate": "300/612", "decoder": "TERMINATED_SOFT_VITERBI_FLOAT", "decision": "SOFT_FLOAT", "channel": "BPSK_AWGN_NO_BURST", "interleaver": "NONE", "snrDefinition": "Es/N0", "snrStart": -5, "snrStop": 10, "snrStep": 0.5, "pointCount": len(cc_points), "matchedToS7": "true", "matchReason": "Exact K=7 171/133 rate-1/2 mother code, 300 payload, 6 zero tails, 612 coded bits, soft terminated Viterbi", "legacySource": "true", "usedForPlot": "true", "sha256": digest(CC_SOURCE)})
    excluded = [
        {"scheme": "BCH", "metric": "BER/FER/LATENCY", "sourceCsvAbsolutePath": str((REPO / "Report/data/frozen/bch/s2_09_stage06_awgn_formal_figure_data.csv").resolve()), "sourceStage": "BCH_S2_stage06_awgn_formal", "sourceConfigurationId": "K200_M255K207", "payloadBits": 200, "encodedBits": 248, "codeRate": "200/248", "decoder": "BERLEKAMP_MASSEY_CHIEN", "decision": "HARD", "channel": "BPSK_AWGN_NO_BURST", "interleaver": "NONE", "snrDefinition": "Eb/N0 plus derived waveform SNR", "snrStart": "", "snrStop": "", "snrStep": "", "pointCount": "", "matchedToS7": "false", "matchReason": "Excluded: BCH(255,207) shortened block code and encoded length 248 do not match 19xBCH(15,11,1)/285", "legacySource": "true", "usedForPlot": "false", "sha256": digest(REPO / "Report/data/frozen/bch/s2_09_stage06_awgn_formal_figure_data.csv")},
        {"scheme": "CC", "metric": "BER/FER/LATENCY", "sourceCsvAbsolutePath": str(CC_SOURCE.resolve()), "sourceStage": "Task/CC/simulation/S3/stage09_awgn_formal", "sourceConfigurationId": "CC-B-R12-H", "payloadBits": 300, "encodedBits": 612, "codeRate": "300/612", "decoder": "TERMINATED_HARD_VITERBI", "decision": "HARD", "channel": "BPSK_AWGN_NO_BURST", "interleaver": "NONE", "snrDefinition": "Es/N0", "snrStart": -5, "snrStop": 10, "snrStep": 0.5, "pointCount": 31, "matchedToS7": "false", "matchReason": "Excluded: hard-decision Viterbi does not match S7 FLOAT_SOFT", "legacySource": "true", "usedForPlot": "false", "sha256": digest(CC_SOURCE)},
        {"scheme": "CC", "metric": "BER/FER/LATENCY", "sourceCsvAbsolutePath": str((REPO / "Report/data/frozen/cc/s3_17_stage09_two_level_merged_point_results.csv").resolve()), "sourceStage": "Report frozen duplicate", "sourceConfigurationId": "CC-B-R12-S", "payloadBits": 300, "encodedBits": 612, "codeRate": "300/612", "decoder": "TERMINATED_SOFT_VITERBI_FLOAT", "decision": "SOFT_FLOAT", "channel": "BPSK_AWGN_NO_BURST", "interleaver": "NONE", "snrDefinition": "Es/N0", "snrStart": -5, "snrStop": 10, "snrStep": 0.5, "pointCount": 31, "matchedToS7": "true", "matchReason": "Valid duplicate excluded in favor of the original Task/CC Stage09 CSV", "legacySource": "true", "usedForPlot": "false", "sha256": digest(REPO / "Report/data/frozen/cc/s3_17_stage09_two_level_merged_point_results.csv")},
    ]
    return fields, common + excluded


def main():
    bch = normalize_bch()
    cc = normalize_cc()
    normalized_fields = ["scheme", "configurationId", "EsN0Db", "BER", "FER", "decodeTimeMeanNs", "decodeTimeP95Ns", "decodeTimeP99Ns", "decodeTimeMaxNs", "framesProcessed", "sourceCsvAbsolutePath", "sourceStage", "sourceConfigurationId", "sourceRowKey", "snrMapping", "interpolated", "synthetic"]
    write_csv(OUTPUT / "bch" / "no_burst_baseline.csv", normalized_fields, bch)
    write_csv(OUTPUT / "cc" / "no_burst_baseline.csv", normalized_fields, cc)
    (OUTPUT / "bch" / "readme.txt").write_text("BCH 无突发 AWGN 规范化视图；仅做已审计 SNR 口径换算，不插值、不平滑、不重跑。\n", encoding="utf-8")
    (OUTPUT / "cc" / "readme.txt").write_text("CC 无突发 AWGN 规范化视图；仅抽取原始 -5～10 dB/0.5 dB 粗网格，不插值、不平滑、不重跑。\n", encoding="utf-8")
    fields, audit = audit_rows(bch, cc)
    write_csv(OUTPUT / "baseline_source_audit.csv", fields, audit)
    (OUTPUT / "baseline_source_audit.md").write_text(f"""# S7 无突发 AWGN 历史数据匹配审计

## BCH

采用 `{BCH_SOURCE.resolve()}` 的 `K200_S15`。原始 37 点逐行明确 `payloadLength=200`、`motherN/K/T=15/11/1`、`blockCount=19`、`encodedLength=285` 和 `actualRate=200/285`；Stage07 复用已审计 syndrome-lookup 硬判决链路。其 `sigma2=10^(-snrDb/10)`，与 S7 `sigma2=0.5*10^(-EsN0Db/10)` 严格等价于 `EsN0Db=snrDb-10log10(2)`。当前图只保留换算后落入 -5～10 dB 的 {len(bch)} 个原始点；未插值。

## CC

采用 `{CC_SOURCE.resolve()}` 的 `CC-B-R12-S`。Stage01/Stage09 冻结证据给出 payload=300、K=7、171/133、6 个零尾、N=612、SOFT_FLOAT、BPSK-AWGN 和 Es/N0。只抽取恰好落在 S7 -5～10 dB/0.5 dB 网格的 {len(cc)} 个原始点；密集层额外点未用于补点。

## 排除项

- BCH Stage06 `K200_M255K207`：编码结构和长度为 shortened BCH(255,207)/248 bit，不匹配。
- CC `CC-B-R12-H`：硬判决 Viterbi，不匹配 S7 软判决。
- Report frozen CC CSV：内容哈希与原始 Stage09 CSV一致，仅为重复副本，优先引用原始 Stage 文件。
- 打孔 R=2/3、3/4、连续未终止、其他 payload/码长及 Eb/N0 口径不明的数据均未使用。

## 时延与复杂度

两份历史 CSV 均含逐点平均译码时间；Stage15 使用帧数加权平均，仅作为纯译码 CPU 时间。历史结果没有与 S7 当前图一致的复杂度操作计数，因此复杂度基线明确为 N/A，不进行推断。无突发无交织的交织/解交织 CPU 为 N/A；buffer=0 是结构定义，不是历史仿真统计。

NO_FORMAL_RERUN
""", encoding="utf-8")
    (OUTPUT / "readme.txt").write_text("S7 历史无突发 AWGN 基线、逐项匹配审计和规范化只读映射。严禁把本目录当作新仿真结果。\n", encoding="utf-8")
    hashes = {str(path.resolve()): digest(path) for path in (FORMAL["BCH"], FORMAL["CC"], BCH_SOURCE, CC_SOURCE)}
    (OUTPUT / "original_input_hashes.json").write_text(json.dumps({"before": hashes, "noFormalRerun": True}, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_S7_NO_BURST_BASELINE_COLLECTION BCH={len(bch)} CC={len(cc)}")


if __name__ == "__main__":
    main()
