#!/usr/bin/env python3
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = pathlib.Path(__file__).resolve().parents[4]
S6 = ROOT / "Task" / "Comparison" / "S6"
BCH = S6 / "results" / "bch" / "formal_v02_20260804" / "bch_formal_results.csv"
BCH_COMPLEX = S6 / "results" / "bch" / "formal_v02_20260804" / "bch_complexity_results.csv"
BCH_MEMORY = S6 / "results" / "bch" / "formal_v02_20260804" / "bch_memory_results.csv"
CC = S6 / "results" / "cc" / "cc_integrated_results.csv"
LDPC = S6 / "results" / "ldpc" / "ldpc_n560_integrated_results.csv"
OUTPUT = S6 / "results" / "summary" / "figures"
SCRIPT = pathlib.Path(__file__).resolve()
README = SCRIPT.parent / "generated_figure_readme.txt"
PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#999999")
LINES = ("-", "--", "-.", ":")
MARKERS = ("o", "s", "^", "D", "v", "P", "X", "h")


def sha256(path):
    value = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with pathlib.Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def font():
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("no Chinese font")


FONT = font()
COMMIT = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def finish(directory, figure_id, title, sources, x_label, y_label, log_scale,
           legends, colors, line_styles, markers, zero_count, derivation="NONE"):
    png = directory / "figure.png"
    data = directory / "figure_data.csv"
    manifest = {
        "figureId": figure_id, "title": title,
        "sourceFiles": [path.relative_to(ROOT).as_posix() for path in sources],
        "sourceFileHashes": [sha256(path) for path in sources],
        "xColumn": "esN0Db" if "信噪比" in x_label else "category",
        "yColumns": ["rawValue"], "xLabel": x_label, "yLabel": y_label,
        "xUnit": "dB" if "信噪比" in x_label else "category", "yUnit": y_label,
        "xTransform": "NONE", "yTransform": "LOG10_DISPLAY" if log_scale else "NONE",
        "logScale": log_scale,
        "zeroValuePolicy": "原始零值保留，plotValue留空且不在对数轴绘制" if log_scale else "按值绘制",
        "missingValuePolicy": "缺失即阻断", "interpolation": "NONE", "smoothing": "NONE",
        "legendEntries": legends, "colors": colors, "lineStyles": line_styles, "markers": markers,
        "derivation": derivation,
        "outputPng": png.relative_to(ROOT).as_posix(), "outputCsv": data.relative_to(ROOT).as_posix(),
        "outputHash": sha256(png), "outputCsvHash": sha256(data),
        "scriptPath": SCRIPT.relative_to(ROOT).as_posix(), "scriptSha256": sha256(SCRIPT),
        "gitCommit": COMMIT, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "chineseFont": FONT, "preservedZeroRows": zero_count,
    }
    (directory / "plot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "readme.txt").write_bytes(README.read_bytes())
    return {"figureId": figure_id, "title": title, "pngSha256": manifest["outputHash"],
            "zeroRows": zero_count, "gate": "PASS"}


def line_plot(figure_id, title, source, rows, group_field, group_labels, y_field, y_label, log_scale=False):
    directory = OUTPUT / figure_id
    if directory.exists():
        raise RuntimeError(f"refuse overwrite: {directory}")
    directory.mkdir()
    output_rows, curves, zero_count = [], [], 0
    for index, (group, label) in enumerate(group_labels.items()):
        selected = sorted((row for row in rows if row[group_field] == group), key=lambda row: float(row["esN0Db"]))
        if len(selected) != 31:
            raise RuntimeError(f"{figure_id}/{group} points != 31")
        xs, ys = [], []
        for row in selected:
            raw = float(row[y_field])
            if not math.isfinite(raw):
                raise RuntimeError(f"non-finite {figure_id}")
            is_zero = raw == 0.0
            plotted = not (log_scale and is_zero)
            zero_count += int(is_zero)
            xs.append(float(row["esN0Db"]))
            ys.append(raw if plotted else math.nan)
            frames = int(float(row.get("processedFrames", row.get("frames", 0))))
            output_rows.append({"figureId": figure_id, "series": label, "esN0Db": row["esN0Db"],
                                "rawValue": format(raw, ".17g"), "plotValue": format(raw, ".17g") if plotted else "",
                                "isPlotted": str(plotted).lower(), "isZero": str(is_zero).lower(),
                                "zeroErrorUpperBound95": format(3.0 / frames, ".17g") if is_zero and frames else ""})
        curves.append((xs, ys, label, PALETTE[index], LINES[index % len(LINES)], MARKERS[index]))
    write_csv(directory / "figure_data.csv", output_rows)
    fig, axis = plt.subplots(figsize=(8.6, 5.6), dpi=180)
    for xs, ys, label, color, line, marker in curves:
        axis.plot(xs, ys, label=label, color=color, linestyle=line, marker=marker, linewidth=1.5, markersize=3.5)
    if log_scale:
        axis.set_yscale("log")
    axis.set_xlabel("符号信噪比 Es/N0（dB）")
    axis.set_ylabel(y_label)
    axis.set_title(title)
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    fig.tight_layout(); fig.savefig(directory / "figure.png", dpi=180); plt.close(fig)
    return finish(directory, figure_id, title, [source], "符号信噪比 Es/N0（dB）", y_label, log_scale,
                  [value for value in group_labels.values()], [curve[3] for curve in curves],
                  [curve[4] for curve in curves], [curve[5] for curve in curves], zero_count)


def bar_plot(figure_id, title, sources, categories, series, y_label, derivation):
    directory = OUTPUT / figure_id
    if directory.exists():
        raise RuntimeError(f"refuse overwrite: {directory}")
    directory.mkdir()
    output_rows = []
    for series_name, values in series.items():
        for category, value in zip(categories, values):
            if not math.isfinite(value) or value < 0:
                raise RuntimeError(f"invalid bar value: {figure_id}")
            output_rows.append({"figureId": figure_id, "series": series_name, "category": category,
                                "rawValue": format(value, ".17g"), "plotValue": format(value, ".17g"),
                                "isPlotted": "true", "isZero": str(value == 0).lower(), "zeroErrorUpperBound95": ""})
    write_csv(directory / "figure_data.csv", output_rows)
    fig, axis = plt.subplots(figsize=(9.4, 5.8), dpi=180)
    count = len(series); width = 0.8 / max(1, count); base = list(range(len(categories)))
    for index, (name, values) in enumerate(series.items()):
        positions = [x - 0.4 + width / 2 + index * width for x in base]
        axis.bar(positions, values, width=width, label=name, color=PALETTE[index])
    axis.set_xticks(base, categories, rotation=20, ha="right")
    axis.set_ylabel(y_label); axis.set_title(title); axis.grid(True, axis="y", alpha=0.25); axis.legend()
    fig.tight_layout(); fig.savefig(directory / "figure.png", dpi=180); plt.close(fig)
    return finish(directory, figure_id, title, sources, "方案/操作类别", y_label, False,
                  list(series), list(PALETTE[:len(series)]), ["bar"] * len(series), ["none"] * len(series),
                  sum(value == 0 for values in series.values() for value in values), derivation)


def mean(values):
    return sum(values) / len(values)


def main():
    for path in (BCH, BCH_COMPLEX, BCH_MEMORY, CC, LDPC):
        if not path.exists(): raise RuntimeError(f"missing source: {path}")
    if any(path.is_dir() for path in OUTPUT.iterdir()):
        raise RuntimeError("figure output is not empty")
    bch, bc, bm, cc, ldpc = map(read_csv, (BCH, BCH_COMPLEX, BCH_MEMORY, CC, LDPC))
    results = []
    bch_groups = {"BCH-S200": "分组 BCH-S200", "BCH-B200": "整块 BCH-B200"}
    for fid, title, field, label, log in (
        ("bch_01_ber", "200比特BCH误码率对比", "BER", "误码率 BER", True),
        ("bch_02_fer", "200比特BCH误帧率对比", "FER", "误帧率 FER", True),
        ("bch_07_avg_time", "200比特BCH平均译码时延", "avgDecodeTimeUs", "平均译码时延（μs）", False),
        ("bch_08_p95_time", "200比特BCH第95百分位译码时延", "p95DecodeTimeUs", "P95译码时延（μs）", False),
        ("bch_09_p99_time", "200比特BCH第99百分位译码时延", "p99DecodeTimeUs", "P99译码时延（μs）", False),
        ("bch_10_max_time", "200比特BCH最大译码时延观测", "maxDecodeTimeUs", "最大译码时延（μs）", False)):
        results.append(line_plot(fid, title, BCH, bch, "caseName", bch_groups, field, label, log))
    def complexity_lines(case, metrics, fid, title):
        rows = [row for row in bc if row["caseName"] == case and row["metric"] in metrics]
        labels = {metric: label for metric, label in metrics.items()}
        return line_plot(fid, title, BCH_COMPLEX, rows, "metric", labels, "average", "平均操作次数/帧")
    results.append(complexity_lines("BCH-S200", {
        "syndromeCalculationCount": "综合征计算", "syndromeBitTestCount": "综合征位测试",
        "tableLookupCount": "查表", "bitFlipCount": "比特翻转", "postSyndromeCheckCount": "译后综合征检查"},
        "bch_03_segmented_operations", "分组BCH平均译码操作量"))
    results.append(complexity_lines("BCH-B200", {
        "syndromeEvaluationCount": "综合征求值", "bmIterationCount": "BM迭代",
        "chienPositionTestCount": "Chien位置测试", "gfAddCount": "有限域加法",
        "gfMultiplyCount": "有限域乘法", "gfDivideCount": "有限域除法"},
        "bch_04_block_operations", "整块BCH平均译码操作量"))
    structure_categories = ["S200综合征计算", "S200查表", "B200 BM迭代", "B200 Chien位置测试"]
    structure_values = []
    for case, metric in (("BCH-S200", "syndromeCalculationCount"), ("BCH-S200", "tableLookupCount"),
                         ("BCH-B200", "bmIterationCount"), ("BCH-B200", "chienPositionTestCount")):
        structure_values.append(mean([float(row["average"]) for row in bc if row["caseName"] == case and row["metric"] == metric]))
    results.append(bar_plot("bch_05_operation_structure", "BCH译码操作结构对比", [BCH_COMPLEX],
                            structure_categories, {"网格均值（操作/帧）": structure_values}, "平均操作次数/帧",
                            "各类别分别统计；不同操作类型并非等价硬件代价，不做总和"))
    mem_categories, total_mem, workspace = [], [], []
    for case, label in bch_groups.items():
        selected = [row for row in bm if row["caseName"] == case]
        mem_categories.append(label); total_mem.append(max(float(row["totalDecoderMemoryBytes"]) for row in selected)); workspace.append(max(float(row["peakWorkspaceBytes"]) for row in selected))
    results.append(bar_plot("bch_06_memory", "BCH译码存储开销对比", [BCH_MEMORY], mem_categories,
                            {"译码器总内存": total_mem, "峰值工作区": workspace}, "存储量（byte）",
                            "Formal全网格逐点峰值的最大值；EXACT_FROM_TYPE_AND_COUNT"))
    block = [row for row in cc if row["organizationMode"] == "BLOCK"]
    slot = [row for row in cc if row["organizationMode"] == "SLOT"]
    block_groups = {"BLOCK_HARD": "整块硬判决", "BLOCK_FLOAT_SOFT": "整块浮点软判决"}
    slot_groups = {name: name.replace("_FLOAT_SOFT", " 浮点软判决").replace("_HARD", " 硬判决") for name in sorted({row["schemeId"] for row in slot})}
    results.append(line_plot("cc_01_block_ber", "整块卷积码硬软判决误码率", CC, block, "schemeId", block_groups, "BER", "误码率 BER", True))
    results.append(line_plot("cc_02_block_fer", "整块卷积码硬软判决误帧率", CC, block, "schemeId", block_groups, "FER", "误帧率 FER", True))
    results.append(line_plot("cc_03_slot_fer", "时隙卷积码硬软判决误帧率", CC, slot, "schemeId", slot_groups, "FER", "误帧率 FER", True))
    schemes = sorted({row["schemeId"] for row in cc})
    acs = [mean([float(row["ACSCount"]) / float(row["frames"]) for row in cc if row["schemeId"] == scheme]) for scheme in schemes]
    traceback = [mean([float(row["tracebackOperations"]) / float(row["frames"]) for row in cc if row["schemeId"] == scheme]) for scheme in schemes]
    results.append(bar_plot("cc_04_complexity", "卷积码译码复杂度对比", [CC], schemes,
                            {"ACS/帧": acs, "回溯操作/帧": traceback}, "平均操作次数/帧",
                            "全Es/N0网格逐点每帧计数的均值；ACS与回溯操作不视为等价代价"))
    memory = [max(float(row["decoderMemoryBytes"]) for row in cc if row["schemeId"] == scheme) for scheme in schemes]
    results.append(bar_plot("cc_05_memory", "卷积码译码存储开销对比", [CC], schemes, {"译码内存": memory}, "存储量（byte）", "源Formal totalMemoryBytes"))
    all_groups = {name: name.replace("_FLOAT_SOFT", " 浮点软判决").replace("_HARD", " 硬判决") for name in schemes}
    results.append(line_plot("cc_06_avg_time", "卷积码平均译码时延", CC, cc, "schemeId", all_groups, "avgCpuDecodeTimeUs", "CPU平均译码时延（μs）"))
    results.append(line_plot("cc_07_first_output", "时隙卷积码首输出时延", CC, slot, "schemeId", slot_groups, "firstOutputDelaySymbols", "首输出时延（符号）"))
    results.append(line_plot("cc_08_decision_delay", "时隙卷积码决策时延", CC, slot, "schemeId", slot_groups, "p95DecisionDelaySymbols", "P95决策时延（符号）"))
    ldpc_groups = {"BP": "BP", "NMS": "NMS（α=0.95）"}
    for fid, title, field, label, log in (
        ("ldpc_01_ber", "N560 BP与NMS误码率", "BER", "误码率 BER", True),
        ("ldpc_02_fer", "N560 BP与NMS误帧率", "FER", "误帧率 FER", True),
        ("ldpc_03_iterations", "N560 BP与NMS平均迭代次数", "avgIterations", "平均迭代次数", False),
        ("ldpc_04_early_stop", "N560 BP与NMS提前停止比例", "earlyStopRate", "提前停止比例", False),
        ("ldpc_07_avg_time", "N560 BP与NMS平均译码时延", "avgDecodeTimeUs", "平均译码时延（μs）", False),
        ("ldpc_08_max_time", "N560 BP与NMS最大译码时延观测", "maxDecodeTimeUs", "最大译码时延（μs）", False)):
        results.append(line_plot(fid, title, LDPC, ldpc, "algorithm", ldpc_groups, field, label, log))
    op_fields = (("tanhCount", "tanh"), ("atanhCount", "atanh"), ("absCount", "绝对值"),
                 ("comparisonCount", "比较"), ("min1Min2Count", "最小值"), ("alphaScaleCount", "α缩放"))
    op_series = {}
    for algorithm in ldpc_groups:
        op_series[ldpc_groups[algorithm]] = [mean([float(row[field]) / float(row["frames"]) for row in ldpc if row["algorithm"] == algorithm]) for field, _ in op_fields]
    results.append(bar_plot("ldpc_05_complexity", "N560 BP与NMS译码复杂度", [LDPC], [label for _, label in op_fields],
                            op_series, "平均操作次数/帧", "全Es/N0网格逐点每帧操作计数均值；不同类别不相加"))
    ldpc_mem = [max(float(row["decoderMemoryBytes"]) for row in ldpc if row["algorithm"] == algorithm) for algorithm in ldpc_groups]
    results.append(bar_plot("ldpc_06_memory", "N560 BP与NMS存储开销", [LDPC], list(ldpc_groups.values()), {"译码内存": ldpc_mem}, "存储量（byte）", "源Formal decoderMemoryBytes"))
    if len(results) != 26:
        raise RuntimeError(f"S6 figure count {len(results)} != 26")
    summary = {"schemaVersion": "s6.scientific.plots.v1", "figureCount": 26,
               "moduleCounts": {"BCH": 10, "CC": 8, "LDPC": 8},
               "preservedZeroRows": sum(row["zeroRows"] for row in results),
               "figures": results, "gate": "PASS_S6_SCIENTIFIC_PLOTS"}
    (OUTPUT.parent / "s6_plot_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summary["gate"], "figures=26")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
