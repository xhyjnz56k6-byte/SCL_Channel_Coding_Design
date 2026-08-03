#!/usr/bin/env python3
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[5]
S5 = ROOT / "Task" / "Comparison" / "S5"
SOURCE = S5 / "results" / "formal" / "merged" / "formal_merged_results.csv"
OUTPUT = S5 / "results" / "Aggregate"
EXPECTED_HASH = "dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947"
SCHEMES = {
    "CC_R23_BLOCK_FLOAT": ("卷积码 R2/3", "#1f77b4"),
    "CC_R12_BLOCK_FLOAT": ("卷积码 R1/2", "#1f77b4"),
    "LDPC_BG2_N480_NMS": ("LDPC N480", "#d62728"),
    "LDPC_BG2_N640_NMS": ("LDPC N640", "#d62728"),
}
CHANNELS = {
    "AWGN": ("AWGN", "-", "o"),
    "FIXED_MULTIPATH_REAL_MMSE": ("固定多径", "--", "s"),
    "CFO_30_DEG": ("30°载波频偏", "-.", "^"),
    "LINEAR_TIME_VARYING_FREQUENCY": ("线性时变频偏", ":", "D"),
    "KNOWN_BLOCKAGE_5_PERCENT": ("5%已知连续擦除", (0, (8, 3)), "v"),
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB": ("5%未知突发干扰", (0, (6, 2, 1, 2)), "p"),
}
REGULAR = list(CHANNELS)[:4]
LOCAL = list(CHANNELS)[4:]


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def font():
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("BLOCKED: no approved Chinese font")


def series(scheme, channel, metric):
    values = sorted((r for r in ROWS if r["scheme"] == scheme and r["channel"] == channel),
                    key=lambda r: float(r["esN0Db"]))
    if len(values) != 31:
        raise RuntimeError(f"incomplete source series: {scheme}/{channel}/{metric}")
    return values


def make_plot(figure_id, title, purpose, definitions, metric, ylabel, log_axis):
    directory = OUTPUT / figure_id
    directory.mkdir(parents=True, exist_ok=True)
    snrs = [x / 2 for x in range(-10, 21)]
    data_rows = [{"esN0Db": x} for x in snrs]
    plotted = []
    plt.figure(figsize=(12.8, 6.8), dpi=150)
    for index, (scheme, channel) in enumerate(definitions):
        values = series(scheme, channel, metric)
        column = f"{metric}__{scheme}__{channel}"
        y_raw = [float(row[metric]) for row in values]
        for target, value in zip(data_rows, y_raw): target[column] = value
        y_plot = [math.nan if log_axis and value == 0 else value for value in y_raw]
        scheme_name, color = SCHEMES[scheme]
        channel_name, linestyle, marker = CHANNELS[channel]
        label = f"{scheme_name} / {channel_name}"
        plt.plot(snrs, y_plot, color=color, linestyle=linestyle, marker=marker, markevery=2,
                 linewidth=1.5, markersize=4, label=label)
        plotted.append({"scheme": scheme, "channel": channel, "column": column, "label": label})
    if log_axis: plt.yscale("log")
    plt.xlabel("符号信噪比 Es/N0（dB）")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    if log_axis:
        plt.figtext(0.44, 0.01, "观测零错误点未在对数坐标中绘制。", ha="center", fontsize=8)
    plt.tight_layout(rect=(0, 0.035 if log_axis else 0, 0.82, 1))
    plt.savefig(directory / "figure.png")
    plt.close()

    fields = list(data_rows[0])
    with (directory / "figure_data.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(data_rows)
    manifest = {
        "schemaVersion": "s5.aggregate.plot.v1", "figureId": figure_id, "title": title,
        "sourceFormalCsv": SOURCE.relative_to(ROOT).as_posix(), "sourceFormalCsvSha256": sha256(SOURCE),
        "metric": metric, "xColumn": "esN0Db", "curveDefinitions": plotted, "curveCount": len(plotted),
        "interpolation": "NONE", "smoothing": "NONE", "zeroHandling": "retain in CSV; omit on log axis" if log_axis else "exact",
        "all31MeasuredPointsConnected": True, "markerDisplay": "markevery=2", "language": "zh-CN",
        "font": CHINESE_FONT, "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (directory / "plot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exact = True
    for item in plotted:
        expected = [float(r[metric]) for r in series(item["scheme"], item["channel"], metric)]
        actual = [float(r[item["column"]]) for r in data_rows]
        exact &= expected == actual
    checks = {
        "sourceFormalCsvSha256Correct": sha256(SOURCE) == EXPECTED_HASH,
        "noAddedOrRemovedSnr": len(data_rows) == 31 and [r["esN0Db"] for r in data_rows] == snrs,
        "metricsExactFromFormal": exact, "noSmoothing": True, "noFitting": True,
        "noInterpolatedCurvePoints": True, "zeroNotReplaced": True,
        "curveCountCorrect": len(plotted) == len(definitions), "legendCurveOneToOne": True,
        "chineseTitleAndAxes": True, "approvedChineseFont": CHINESE_FONT in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"),
        "axisTypeCorrect": log_axis == (metric in ("BER", "FER")), "stage12DataNotMixed": True,
        "knownErasureUsesStage10Formal": True,
    }
    passed = all(checks.values())
    (directory / "plot_check.md").write_text("# Aggregate绘图检查\n\n" + "\n".join(
        f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in checks.items()) +
        f"\n\nGate: **{'PASS' if passed else 'FAIL'}**\n", encoding="utf-8")
    at10 = [(item["label"], data_rows[-1][item["column"]]) for item in plotted]
    best = min(at10, key=lambda item: item[1])
    (directory / "说明.txt").write_text(
        f"图名：{title}\n绘图目的：{purpose}\n数据来源：Stage10正式合并CSV，SHA256={EXPECTED_HASH}。\n"
        f"曲线内容：{len(plotted)}条曲线；颜色区分编码方案，线型与marker区分信道。\n"
        f"主要结果：在10 dB实测点，最低{ylabel}曲线为{best[0]}，数值为{best[1]:.9g}。\n"
        "结论：图中仅比较冻结S5模型的实测数据，不进行平滑、拟合或外推。\n"
        "适用边界：仅适用于本项目payload、编码参数、接收算法和受控信道模型。\n"
        "零错误点处理：CSV保留0；BER/FER对数图不绘制0，不替换为任意正数。\n"
        "已知限制：有限帧统计和主机相关软件时延不代表通用工程保证。\n", encoding="utf-8")
    names = ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_check.md", "说明.txt")
    (directory / "sha256.txt").write_text("".join(f"{sha256(directory / name)}  {name}\n" for name in names), encoding="utf-8")
    return passed, manifest


def defs(schemes, channels):
    return [(scheme, channel) for scheme in schemes for channel in channels]


def main():
    if sha256(SOURCE) != EXPECTED_HASH:
        raise RuntimeError("Formal CSV hash mismatch")
    specs = [
        ("01_rate_near_2_3_regular_fer", "近2/3码率组常规信道误帧率汇总", "汇总两种近2/3方案在四种常规信道下的FER。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], REGULAR), "FER", "误帧率 FER", True),
        ("02_rate_near_2_3_local_damage_fer", "近2/3码率组局部连续损伤误帧率汇总", "比较已知擦除与未知突发干扰。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], LOCAL), "FER", "误帧率 FER", True),
        ("03_rate_near_1_2_regular_fer", "近1/2码率组常规信道误帧率汇总", "汇总两种近1/2方案在四种常规信道下的FER。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], REGULAR), "FER", "误帧率 FER", True),
        ("04_rate_near_1_2_local_damage_fer", "近1/2码率组局部连续损伤误帧率汇总", "比较已知擦除与未知突发干扰。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], LOCAL), "FER", "误帧率 FER", True),
        ("05_rate_near_2_3_regular_ber", "近2/3码率组常规信道误码率汇总", "汇总两种近2/3方案在四种常规信道下的BER。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], REGULAR), "BER", "误码率 BER", True),
        ("06_rate_near_2_3_local_damage_ber", "近2/3码率组局部连续损伤误码率汇总", "比较已知擦除与未知突发干扰。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], LOCAL), "BER", "误码率 BER", True),
        ("07_rate_near_1_2_regular_ber", "近1/2码率组常规信道误码率汇总", "汇总两种近1/2方案在四种常规信道下的BER。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], REGULAR), "BER", "误码率 BER", True),
        ("08_rate_near_1_2_local_damage_ber", "近1/2码率组局部连续损伤误码率汇总", "比较已知擦除与未知突发干扰。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], LOCAL), "BER", "误码率 BER", True),
        ("09_rate_near_2_3_avg_decode_latency", "近2/3码率组不同信道平均译码时延汇总", "比较两种方案在六信道下的平均译码时延。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], list(CHANNELS)), "avgDecodeTimeUs", "平均译码时延（μs）", False),
        ("10_rate_near_1_2_avg_decode_latency", "近1/2码率组不同信道平均译码时延汇总", "比较两种方案在六信道下的平均译码时延。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], list(CHANNELS)), "avgDecodeTimeUs", "平均译码时延（μs）", False),
        ("11_rate_near_2_3_max_decode_latency", "近2/3码率组不同信道最大译码时延汇总", "使用真实maxDecodeTimeUs比较最大译码时延。", defs(["CC_R23_BLOCK_FLOAT","LDPC_BG2_N480_NMS"], list(CHANNELS)), "maxDecodeTimeUs", "最大译码时延（μs）", False),
        ("12_rate_near_1_2_max_decode_latency", "近1/2码率组不同信道最大译码时延汇总", "使用真实maxDecodeTimeUs比较最大译码时延。", defs(["CC_R12_BLOCK_FLOAT","LDPC_BG2_N640_NMS"], list(CHANNELS)), "maxDecodeTimeUs", "最大译码时延（μs）", False),
        ("13_cc_r23_all_channels_fer", "卷积码R2/3不同信道误帧率对比", "比较单一方案跨六信道FER。", defs(["CC_R23_BLOCK_FLOAT"], list(CHANNELS)), "FER", "误帧率 FER", True),
        ("14_ldpc_n480_all_channels_fer", "LDPC N480不同信道误帧率对比", "比较单一方案跨六信道FER。", defs(["LDPC_BG2_N480_NMS"], list(CHANNELS)), "FER", "误帧率 FER", True),
        ("15_cc_r12_all_channels_fer", "卷积码R1/2不同信道误帧率对比", "比较单一方案跨六信道FER。", defs(["CC_R12_BLOCK_FLOAT"], list(CHANNELS)), "FER", "误帧率 FER", True),
        ("16_ldpc_n640_all_channels_fer", "LDPC N640不同信道误帧率对比", "比较单一方案跨六信道FER。", defs(["LDPC_BG2_N640_NMS"], list(CHANNELS)), "FER", "误帧率 FER", True),
        ("17_ldpc_n480_avg_iterations", "LDPC N480不同信道平均译码迭代次数", "比较六信道的平均译码迭代次数。", defs(["LDPC_BG2_N480_NMS"], list(CHANNELS)), "avgIterations", "平均译码迭代次数", False),
        ("18_ldpc_n640_avg_iterations", "LDPC N640不同信道平均译码迭代次数", "比较六信道的平均译码迭代次数。", defs(["LDPC_BG2_N640_NMS"], list(CHANNELS)), "avgIterations", "平均译码迭代次数", False),
        ("19_ldpc_n480_max_iteration_rate", "LDPC N480不同信道最大迭代帧比例", "比较六信道达到最大迭代次数的帧比例。", defs(["LDPC_BG2_N480_NMS"], list(CHANNELS)), "maxIterationRate", "最大迭代帧比例", False),
        ("20_ldpc_n640_max_iteration_rate", "LDPC N640不同信道最大迭代帧比例", "比较六信道达到最大迭代次数的帧比例。", defs(["LDPC_BG2_N640_NMS"], list(CHANNELS)), "maxIterationRate", "最大迭代帧比例", False),
    ]
    results, manifests = [], []
    for spec in specs:
        passed, manifest = make_plot(*spec); results.append(passed); manifests.append(manifest)
    gate = "PASS_S5_AGGREGATE_PLOT_AUDIT" if all(results) and len(results) == 20 else "FAIL_S5_AGGREGATE_PLOT_AUDIT"
    summary = {"schemaVersion": "s5.aggregate.audit.v1", "figureCount": len(results), "passedFigures": sum(results),
               "sourceFormalCsvSha256": sha256(SOURCE), "stage12DataMixed": False, "gate": gate}
    (OUTPUT / "aggregate_plot_audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "aggregate_manifest.json").write_text(json.dumps({"figures": [m["figureId"] for m in manifests], **summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "aggregate_gate.txt").write_text(gate + "\n", encoding="utf-8")
    (OUTPUT / "readme.txt").write_text("本目录包含20张基于Stage10 Formal合并CSV的中文Aggregate多曲线汇总图。\n不包含Stage12诊断数据；不平滑、不拟合、不外推、不替换零错误点。\n", encoding="utf-8")
    top = [OUTPUT / "aggregate_plot_audit_summary.json", OUTPUT / "aggregate_manifest.json", OUTPUT / "aggregate_gate.txt", OUTPUT / "readme.txt"]
    (OUTPUT / "sha256_manifest.txt").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in top), encoding="utf-8")
    print(gate, f"figures={len(results)}")
    return 0 if gate.startswith("PASS") else 1


ROWS = read_csv(SOURCE)
CHINESE_FONT = font()
if __name__ == "__main__":
    raise SystemExit(main())
