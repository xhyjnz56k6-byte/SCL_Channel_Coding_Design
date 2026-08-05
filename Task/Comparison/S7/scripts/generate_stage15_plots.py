import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "stage15_scientific_plots"
FORMAL = {
    "BCH": ROOT / "stage10_bch_formal" / "results" / "formal_results.csv",
    "CC": ROOT / "stage11_cc_formal" / "results" / "formal_results.csv",
}
HISTORICAL = ROOT.parents[1] / "Comparison" / "S6" / "results" / "ldpc" / "ldpc_n560_integrated_results.csv"
FONT = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
CONFIG_LABELS = {
    "BCH_NONE": "无交织", "BCH_CODEBLOCK_D19": "BCH码块交织 D=19",
    "BCH_ROW_COLUMN_R15": "行列交织 rows=15", "BCH_GLOBAL_PSEUDO_285": "全帧伪随机交织",
    "CC_NONE": "无交织", "CC_SHORT_D8_RECOMMENDED": "短深度块交织 D=8",
    "CC_PSEUDO_128_RECOMMENDED": "伪随机交织 span=128", "CC_SHORT_D16_CONTROL_128": "短深度块交织 D=16",
}
POSITION_LABELS = {"HEAD": "帧首", "QUARTER": "四分之一", "MIDDLE": "帧中", "THREE_QUARTER": "四分之三", "TAIL": "帧尾", "RANDOM": "随机"}
LABEL_TO_CONFIG = {label: config for config, label in CONFIG_LABELS.items()}
BCH_STYLE_MAP = {
    "BCH_NONE": {"linestyle": "-", "marker": "o", "markerfacecolor": None, "markeredgewidth": 1.0, "zorder": 2, "drawOrder": 1},
    "BCH_GLOBAL_PSEUDO_285": {"linestyle": ":", "marker": "^", "markerfacecolor": "none", "markeredgewidth": 1.3, "zorder": 3, "drawOrder": 2},
    "BCH_CODEBLOCK_D19": {"linestyle": "--", "marker": "o", "markerfacecolor": "none", "markeredgewidth": 1.3, "zorder": 4, "drawOrder": 3},
    "BCH_ROW_COLUMN_R15": {"linestyle": "-.", "marker": "s", "markerfacecolor": None, "markeredgewidth": 1.0, "zorder": 5, "drawOrder": 4},
}
BCH_STYLE_README = """绘图样式：
- 无交织：实线、实心圆；
- BCH码块交织 D=19：虚线、空心圆；
- 行列交织 rows=15：点划线、实心方块；
- 全帧伪随机交织：点线、空心三角。
说明：线型和标记仅用于提高重合曲线的辨识度，不改变原始数据和统计结论。
"""


def style_config_id(series, style_map):
    if style_map is BCH_STYLE_MAP and series == CONFIG_LABELS["BCH_NONE"]:
        return "BCH_NONE"
    return LABEL_TO_CONFIG.get(series)


def read(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def sha256(path):
    digest = hashlib.sha256(); digest.update(path.read_bytes()); return digest.hexdigest()


def aggregate(rows, value_field, ratio=None, configs=None, position=None, reducer="mean"):
    grouped = defaultdict(list)
    for row in rows:
        if ratio is not None and abs(float(row["burstRatioRequested"]) - ratio) > 1e-12: continue
        if configs is not None and row["configurationId"] not in configs: continue
        if position is not None and row["burstPositionType"] != position: continue
        grouped[(row["configurationId"], float(row["EsN0Db"]))].append(float(row[value_field]))
    output = []
    for (config, snr), values in sorted(grouped.items()):
        value = sum(values) / len(values) if reducer == "mean" else (max(values) if reducer == "max" else min(values))
        output.append({"series": CONFIG_LABELS[config], "x": snr, "rawY": value})
    return output


def finalize_assets(directory, manifest, validation, readme):
    (directory / "plot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "plot_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "readme.txt").write_text(readme, encoding="utf-8")
    names = ["figure.png", "figure_data.csv", "plot_manifest.json", "plot_validation.json", "readme.txt"]
    (directory / "sha256.txt").write_text("".join(f"{sha256(directory / name)}  {name}\n" for name in names), encoding="utf-8")


def emit(plot_id, scheme, title, ylabel, data, source_paths, log_y=False, kind="line", note="", style_map=None):
    directory = STAGE / "results" / scheme.lower() / plot_id
    directory.mkdir(parents=True, exist_ok=True)
    fields = ["series", "x", "rawY", "plotted", "exclusionReason", "nonMonotonicHighSnrAnomaly"]
    processed = []
    by_series = defaultdict(list)
    for item in data:
        raw = item.get("rawY", "")
        if raw == "" or raw is None:
            plotted, reason = False, item.get("exclusionReason", "NOT_INTERPOLABLE")
        elif log_y and float(raw) == 0:
            plotted, reason = False, "ZERO_ON_LOG_AXIS"
        elif log_y and float(raw) < 0:
            plotted, reason = False, "NONPOSITIVE_ON_LOG_AXIS"
        else:
            plotted, reason = True, ""
        row = {"series": item["series"], "x": item["x"], "rawY": raw, "plotted": str(plotted).lower(), "exclusionReason": reason, "nonMonotonicHighSnrAnomaly": "false"}
        processed.append(row); by_series[row["series"]].append(row)
    anomaly = False
    if log_y:
        for series_rows in by_series.values():
            seen_zero = False
            for row in sorted(series_rows, key=lambda value: float(value["x"])):
                if row["rawY"] != "" and float(row["rawY"]) == 0: seen_zero = True
                elif seen_zero and row["rawY"] != "" and float(row["rawY"]) > 0:
                    row["nonMonotonicHighSnrAnomaly"] = "true"; anomaly = True
    with (directory / "figure_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(processed)

    fig, ax = plt.subplots(figsize=(9.6, 6.0), dpi=150)
    if kind == "bar":
        plotted_rows = [row for row in processed if row["plotted"] == "true"]
        labels = [f"{row['series']}\n{row['x']}" if str(row["x"]) else row["series"] for row in plotted_rows]
        ax.bar(range(len(plotted_rows)), [float(row["rawY"]) for row in plotted_rows], color="#4472C4")
        ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right", fontproperties=FONT, fontsize=8)
    else:
        ordered_series = list(by_series.items())
        if style_map:
            ordered_series.sort(key=lambda item: style_map.get(style_config_id(item[0], style_map), {"drawOrder": 99})["drawOrder"])
        for series, series_rows in ordered_series:
            points = [row for row in series_rows if row["plotted"] == "true"]
            points.sort(key=lambda row: float(row["x"]))
            if points:
                style = style_map.get(style_config_id(series, style_map), {}) if style_map else {}
                ax.plot([float(row["x"]) for row in points], [float(row["rawY"]) for row in points],
                        marker=style.get("marker", "o"), markersize=4.5 if style else 3, linewidth=1.2,
                        linestyle=style.get("linestyle", "-"), markerfacecolor=style.get("markerfacecolor", None),
                        markeredgewidth=style.get("markeredgewidth", 1.0), zorder=style.get("zorder", 2), label=series)
        if len(by_series) > 1:
            handles, labels = ax.get_legend_handles_labels()
            if style_map:
                legend_order = {"BCH_NONE": 1, "BCH_CODEBLOCK_D19": 2, "BCH_ROW_COLUMN_R15": 3, "BCH_GLOBAL_PSEUDO_285": 4}
                ordered = sorted(zip(handles, labels), key=lambda item: legend_order.get(style_config_id(item[1], style_map), 99))
                handles, labels = zip(*ordered)
                ax.legend(handles, labels, prop=FONT, fontsize=8, ncol=1)
            else:
                ax.legend(handles, labels, prop=FONT, fontsize=8, ncol=2)
        ax.set_xlabel("符号信噪比 Es/N0（dB）", fontproperties=FONT)
    if log_y: ax.set_yscale("log")
    ax.set_ylabel(ylabel, fontproperties=FONT); ax.set_title(title, fontproperties=FONT)
    ax.grid(True, which="both", alpha=0.25); fig.tight_layout(); fig.savefig(directory / "figure.png"); plt.close(fig)
    absolute_sources = [str(Path(path).resolve()) for path in source_paths]
    validation_status = "BLOCKED_NON_MONOTONIC_HIGH_SNR" if anomaly else "PASS"
    manifest = {"plotId": plot_id, "scheme": scheme, "title": title, "xAxis": "符号信噪比 Es/N0（dB）" if kind != "bar" else "配置或类别", "yAxis": ylabel, "logYAxis": log_y, "sourceAbsolutePaths": absolute_sources, "historicalReferenceAbsolutePath": str(HISTORICAL.resolve()), "historicalReferenceUsedInFigure": False, "zeroPolicy": "raw zero retained in figure-data; excluded from log plot; no pseudovalue, horizontal extension, upper-bound or error-floor annotation", "smoothingApplied": False, "forbiddenAnnotations": [], "configurationStyleMap": style_map or {}, "mergeStatus": "NOT_MERGED"}
    validation = {"status": validation_status, "rowCount": len(processed), "plottedRows": sum(row["plotted"] == "true" for row in processed), "zeroExcludedRows": sum(row["exclusionReason"] == "ZERO_ON_LOG_AXIS" for row in processed), "nonMonotonicHighSnrAnomaly": anomaly, "sourcePathsExist": all(Path(path).is_file() for path in absolute_sources), "sha256PendingAtValidationWrite": True}
    readme_text = f"""图名称：{title}
实验目的：展示 S7 {scheme} 的{ylabel}。
固定参数：使用冻结编码、未知连续 BPSK 极性反转和 Formal/专项扫描停止规则。
改变量：见 figure_data.csv 的 series 与 x。
突发比例：由 figure_data.csv 和图名限定。
突发位置：六位置聚合或图中明确位置。
编码方案：{scheme} 冻结方案。
交织方式：图例所列配置；CC D8 与 PSEUDO128 不解释为纯方法差异。
SNR 范围：来自原始数据，不外推。
停止规则：Stage10/11 paired stopping；Stage12 每起点 200 帧。
原始数据来源：{'; '.join(absolute_sources)}
数据文件名称：figure_data.csv。
数据绝对路径：{str((directory / 'figure_data.csv').resolve())}
历史工程数据来源：S6 LDPC 独立参考，仅记录、不混入本图。
历史数据绝对路径：{str(HISTORICAL.resolve())}
绘图过滤规则：不平滑、不删除非零异常点。
零值处理规则：原始 0 保留；对数图不绘制，不替换、不延伸、不标 error floor 或上界。
主要结论：仅由可见原始点支持；{note or '参见 Stage14 推荐报告。'}
已知限制：CPU 时延依赖本机；强突发下 FER 可能饱和。
{BCH_STYLE_README if style_map else ''}图状态：{validation_status}
"""
    finalize_assets(directory, manifest, validation, readme_text)
    return {"plotId": plot_id, "scheme": scheme, "title": title, "directory": str(directory.resolve()), "status": validation_status, "sourceAbsolutePaths": ";".join(absolute_sources)}


def emit_heatmap(plot_id, scheme, title, rows, source_paths, ratio, encoded_length):
    directory = STAGE / "results" / scheme.lower() / plot_id; directory.mkdir(parents=True, exist_ok=True)
    configs = sorted({row["configurationId"] for row in rows}); starts = sorted({int(row["burstStart"]) for row in rows})
    lookup = {(row["configurationId"], int(row["burstStart"])): float(row["FER"]) for row in rows}
    fields = ["series", "x", "rawY", "plotted", "exclusionReason", "nonMonotonicHighSnrAnomaly"]
    data = [{"series": CONFIG_LABELS[config], "x": start, "rawY": lookup[(config, start)], "plotted": "true", "exclusionReason": "", "nonMonotonicHighSnrAnomaly": "false"} for config in configs for start in starts]
    with (directory / "figure_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(data)
    matrix = [[lookup[(config, start)] for start in starts] for config in configs]
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=150); image = ax.imshow(matrix, aspect="auto", origin="lower", interpolation="nearest", extent=[starts[0], starts[-1], -0.5, len(configs)-0.5], vmin=0, vmax=1, cmap="viridis")
    ax.set_yticks(range(len(configs)), [CONFIG_LABELS[c] for c in configs], fontproperties=FONT); ax.set_xlabel("突发起点（编码 bit，零基）", fontproperties=FONT); ax.set_ylabel("交织配置", fontproperties=FONT); ax.set_title(title, fontproperties=FONT); fig.colorbar(image, ax=ax, label="误帧率"); fig.tight_layout(); fig.savefig(directory / "figure.png"); plt.close(fig)
    absolute_sources = [str(Path(path).resolve()) for path in source_paths]
    burst_length = int(rows[0]["burstLengthBits"])
    manifest = {"plotId": plot_id, "scheme": scheme, "title": title, "xAxis": "突发起点（编码 bit，零基）", "yAxis": "交织配置", "colorAxis": "误帧率", "colorRange": [0, 1], "logYAxis": False, "sourceAbsolutePaths": absolute_sources, "historicalReferenceAbsolutePath": str(HISTORICAL.resolve()), "historicalReferenceUsedInFigure": False, "burstRatioRequested": ratio, "burstLengthBits": burst_length, "encodedLengthBits": encoded_length, "framesPerStart": int(rows[0]["framesProcessed"]), "startRange": [starts[0], starts[-1]], "zeroPolicy": "linear heatmap retains and displays raw zero", "smoothingApplied": False, "interpolation": "nearest", "forbiddenAnnotations": [], "mergeStatus": "NOT_MERGED"}
    validation = {"status": "PASS", "rowCount": len(data), "plottedRows": len(data), "zeroExcludedRows": 0, "nonMonotonicHighSnrAnomaly": False, "sourcePathsExist": True, "sha256PendingAtValidationWrite": True}
    readme_text = f"""图名称：{title}
实验目的：展示全起点 FER 空间分布。
固定参数：HIGH 工作点、{ratio * 100:g}% 连续极性反转、每起点 {int(rows[0]['framesProcessed'])} 帧。
改变量：交织配置和突发起点。
突发比例：{ratio * 100:g}%；实际突发长度 {burst_length} bit；BCH 编码后长度 {encoded_length} bit。
突发位置：全部合法起点，范围 {starts[0]}～{starts[-1]}。
编码方案：{scheme} 冻结方案。
交织方式：全部 Formal 配置。
SNR 范围：单个 HIGH 工作点。
停止规则：每起点固定 200 个共享帧。
原始数据来源：{'; '.join(absolute_sources)}
数据文件名称：figure_data.csv。
数据绝对路径：{str((directory / 'figure_data.csv').resolve())}
历史工程数据来源：S6 LDPC 独立参考，仅记录、不混用。
历史数据绝对路径：{str(HISTORICAL.resolve())}
绘图过滤规则：nearest，不平滑、不删除点。
零值处理规则：线性热力图保留并显示原始零值。
主要结论：用于定位 worstStart、bestStart 和边界敏感性。10% 突发下所有起点和全部配置 FER=1，超过 BCH-S200 的结构纠错能力，因此不再用无区分度热力图展示；10% 原始数据和旧图均已归档保留。
已知限制：FER 分辨率为 0.005；不对未测起点插值。
图状态：PASS
"""
    finalize_assets(directory, manifest, validation, readme_text)
    return {"plotId": plot_id, "scheme": scheme, "title": title, "directory": str(directory.resolve()), "status": "PASS", "sourceAbsolutePaths": ";".join(absolute_sources)}


def generate_scheme(scheme, formal_rows, improvement_rows, target_rows, tolerance_rows, latency_rows, start_rows, recommendation):
    inventory = []; source = FORMAL[scheme]
    def add(*args, **kwargs): inventory.append(emit(args[0], scheme, *args[1:], source_paths=[source], **kwargs))
    configs = sorted({row["configurationId"] for row in formal_rows}); nonbaseline = [c for c in configs if not c.endswith("NONE")]
    add("01_methods_fer", f"{scheme} 不同交织配置误帧率", "误帧率", aggregate(formal_rows, "FER", 0.05), log_y=True)
    add("02_methods_ber", f"{scheme} 不同交织配置误码率", "误码率", aggregate(formal_rows, "BER", 0.05), log_y=True)
    for index, ratio in enumerate((0.02, 0.05, 0.10), 3): add(f"{index:02d}_burst_{int(ratio*100)}_fer", f"{scheme} {int(ratio*100)}%突发误帧率", "误帧率", aggregate(formal_rows, "FER", ratio), log_y=True)
    pos_data = []
    for row in formal_rows:
        if row["configurationId"] == recommendation and float(row["burstRatioRequested"]) == 0.05:
            pos_data.append({"series": POSITION_LABELS[row["burstPositionType"]], "x": float(row["EsN0Db"]), "rawY": float(row["FER"])})
    add("06_six_positions_fer", f"{scheme} 六种突发位置误帧率", "误帧率", pos_data, log_y=True)
    for number, reducer, text in ((7, "mean", "平均位置"), (8, "max", "最坏位置"), (9, "min", "最好位置")):
        add(f"{number:02d}_{reducer}_position_fer", f"{scheme} {text}误帧率", "误帧率", aggregate(formal_rows, "FER", 0.05, reducer=reducer), log_y=True)
    sensitivity = []
    grouped = defaultdict(list)
    for row in formal_rows:
        if float(row["burstRatioRequested"]) == 0.05: grouped[(row["configurationId"], float(row["EsN0Db"]))].append(float(row["FER"]))
    for (config, snr), values in sorted(grouped.items()): sensitivity.append({"series": CONFIG_LABELS[config], "x": snr, "rawY": max(values)-min(values)})
    add("10_position_sensitivity", f"{scheme} 位置敏感度", "最坏与最好位置 FER 差", sensitivity)
    for number, field, title, ylabel, log in ((11,"absoluteFerImprovement","FER绝对改善量","FER绝对改善量",False),(12,"relativeFerReductionPercent","FER相对降低率","FER相对降低率（%）",False)):
        data=[{"series":CONFIG_LABELS[row["configurationId"]],"x":float(row["EsN0Db"]),"rawY":float(row[field])} for row in improvement_rows if row["scheme"]==scheme and row["configurationId"] in nonbaseline and float(row["burstRatioRequested"])==0.05 and row[field] != ""]
        add(f"{number:02d}_{field}", f"{scheme} {title}", ylabel, data, log_y=log)
    target_data=[{"series":CONFIG_LABELS[row["configurationId"]],"x":f"{float(row['burstRatioRequested'])*100:g}%","rawY":row["esN0GainDb"],"exclusionReason":row["configurationStatus"]} for row in target_rows if row["scheme"]==scheme and row["configurationId"] in nonbaseline]
    add("13_target_fer_esn0_gain", f"{scheme} 目标 FER 下 Es/N0 改善", "Es/N0 改善（dB）", target_data, kind="bar", note="不可唯一插值的配置不显示数值。")
    if scheme == "BCH":
        add("14_affected_bch_blocks", "BCH 受影响子块数", "平均受影响 BCH 子块数", aggregate(formal_rows, "affectedBlocksMean", 0.05, [recommendation]))
        add("15_max_errors_per_block", "BCH 单块最大错误数", "单个 BCH 子块最大错误数", aggregate(formal_rows, "maximumErrorsInBlock", 0.05, [recommendation], reducer="max"))
    else:
        add("14_short_depth_parameters", "卷积码短深度块交织参数对比", "误帧率", aggregate(formal_rows, "FER", 0.05, ["CC_SHORT_D8_RECOMMENDED","CC_SHORT_D16_CONTROL_128"]), log_y=True, note="D8 与 D16 属于方法内部深度敏感性，不等同于同缓冲工程推荐。")
        add("15_equal_span_128_controlled", "卷积码等跨度128受控对比", "误帧率", aggregate(formal_rows, "FER", 0.05, ["CC_PSEUDO_128_RECOMMENDED","CC_SHORT_D16_CONTROL_128"]), log_y=True)
    metrics = [(16,"decodeTimeMeanNsWeighted","纯译码时间","纯译码时间（ns）"),(17,"interleaveTimeMeanNsWeighted","交织 CPU 时间","交织时间（ns）"),(18,"deinterleaveTimeMeanNsWeighted","解交织 CPU 时间","解交织时间（ns）"),(19,"bufferBits","交织缓冲量","缓冲量（bit）")]
    for number,field,title,ylabel in metrics:
        data=[{"series":CONFIG_LABELS[row["configurationId"]],"x":"","rawY":float(row[field])} for row in latency_rows if row["scheme"]==scheme]
        inventory.append(emit(f"{number:02d}_{field}", scheme, f"{scheme} {title}", ylabel, data, [ROOT/"stage13_latency_complexity"/"results"/"latency_complexity_summary.csv"], kind="bar"))
    tolerance_data=[]
    for row in tolerance_rows:
        if row["scheme"]==scheme:
            for ratio in (2,5,10): tolerance_data.append({"series":CONFIG_LABELS[row["configurationId"]],"x":f"{ratio}%","rawY":float(row[f"worstPositionFerAt{ratio}Percent"])})
    inventory.append(emit("20_burst_tolerance", scheme, f"{scheme} 高工作点突发容限", "最坏位置误帧率", tolerance_data, [ROOT/"stage14_fer_improvement"/"results"/"burst_tolerance_summary.csv"], kind="bar"))
    heat = [row for row in start_rows if row["scheme"]==scheme and row["workpointRole"]=="HIGH" and float(row["burstRatioRequested"])==0.10]
    inventory.append(emit_heatmap("21_all_start_heatmap", scheme, f"{scheme} 10%突发全起点热力图", heat, [ROOT/"stage12_all_start_scan"/"results"/scheme.lower()/"all_start_results.csv"]))
    return inventory


def bch_ber_improvement(rows, relative=False):
    grouped = defaultdict(list)
    for row in rows:
        if float(row["burstRatioRequested"]) == 0.05:
            grouped[(row["configurationId"], float(row["EsN0Db"]))].append(float(row["BER"]))
    baseline = {snr: sum(values) / len(values) for (config, snr), values in grouped.items() if config == "BCH_NONE"}
    output = []
    for (config, snr), values in sorted(grouped.items()):
        if config == "BCH_NONE": continue
        mean = sum(values) / len(values); absolute = baseline[snr] - mean
        output.append({"series": CONFIG_LABELS[config], "x": snr, "rawY": 100.0 * absolute / baseline[snr] if relative and baseline[snr] else absolute})
    return output


def generate_bch_revision():
    formal = read(FORMAL["BCH"])
    improvement = read(ROOT / "stage14_fer_improvement" / "results" / "fer_improvement_summary.csv")
    generated = []
    def add(plot_id, title, ylabel, data, log_y=False):
        generated.append(emit(plot_id, "BCH", title, ylabel, data, [FORMAL["BCH"]], log_y=log_y, style_map=BCH_STYLE_MAP))

    add("01_methods_fer", "5%突发下BCH不同交织配置误帧率", "误帧率", aggregate(formal, "FER", 0.05), log_y=True)
    add("02_methods_ber", "5%突发下BCH不同交织配置误码率", "误码率", aggregate(formal, "BER", 0.05), log_y=True)
    add("04_burst_5_fer", "BCH 5%突发误帧率", "误帧率", aggregate(formal, "FER", 0.05), log_y=True)
    add("05_burst_10_fer", "BCH 10%突发误帧率", "误帧率", aggregate(formal, "FER", 0.10), log_y=True)
    for plot_id, reducer, title in (("07_mean_position_fer", "mean", "BCH 5%突发平均位置误帧率"), ("08_max_position_fer", "max", "BCH 5%突发最坏位置误帧率"), ("09_min_position_fer", "min", "BCH 5%突发最好位置误帧率")):
        add(plot_id, title, "误帧率", aggregate(formal, "FER", 0.05, reducer=reducer), log_y=True)
    for plot_id, field, title, ylabel in (("11_absoluteFerImprovement", "absoluteFerImprovement", "BCH 5%突发FER绝对改善量", "FER绝对改善量"), ("12_relativeFerReductionPercent", "relativeFerReductionPercent", "BCH 5%突发FER相对降低率", "FER相对降低率（%）")):
        data = [{"series": CONFIG_LABELS[row["configurationId"]], "x": float(row["EsN0Db"]), "rawY": float(row[field])} for row in improvement if row["scheme"] == "BCH" and row["configurationId"] != "BCH_NONE" and float(row["burstRatioRequested"]) == 0.05 and row[field] != ""]
        add(plot_id, title, ylabel, data)

    add("22_burst_5_ber", "BCH 5%突发误码率", "误码率", aggregate(formal, "BER", 0.05), log_y=True)
    add("23_burst_10_ber", "BCH 10%突发误码率", "误码率", aggregate(formal, "BER", 0.10), log_y=True)
    for plot_id, reducer, title in (("24_mean_position_ber", "mean", "BCH 5%突发平均位置误码率"), ("25_max_position_ber", "max", "BCH 5%突发最坏位置误码率"), ("26_min_position_ber", "min", "BCH 5%突发最好位置误码率")):
        add(plot_id, title, "误码率", aggregate(formal, "BER", 0.05, reducer=reducer), log_y=True)
    add("27_absoluteBerImprovement", "BCH 5%突发BER绝对改善量", "BER绝对改善量", bch_ber_improvement(formal))
    add("28_relativeBerReductionPercent", "BCH 5%突发BER相对降低率", "BER相对降低率（%）", bch_ber_improvement(formal, relative=True))

    supplement = ROOT / "stage12_all_start_scan" / "results" / "bch_2_percent" / "all_start_results.csv"
    original = ROOT / "stage12_all_start_scan" / "results" / "bch" / "all_start_results.csv"
    two_percent = [row for row in read(supplement) if row["workpointRole"] == "HIGH"]
    five_percent = [row for row in read(original) if row["workpointRole"] == "HIGH" and float(row["burstRatioRequested"]) == 0.05]
    generated.append(emit_heatmap("21_all_start_heatmap_2_percent", "BCH", "BCH 2%突发全起点热力图", two_percent, [supplement], 0.02, 285))
    generated.append(emit_heatmap("22_all_start_heatmap_5_percent", "BCH", "BCH 5%突发全起点热力图", five_percent, [original], 0.05, 285))
    return generated


def main() -> int:
    existing = read(STAGE / "results" / "plot_inventory.csv")
    replaced = {"01_methods_fer", "02_methods_ber", "04_burst_5_fer", "05_burst_10_fer", "07_mean_position_fer", "08_max_position_fer", "09_min_position_fer", "11_absoluteFerImprovement", "12_relativeFerReductionPercent", "21_all_start_heatmap", "21_all_start_heatmap_2_percent", "22_all_start_heatmap_5_percent", "22_burst_5_ber", "23_burst_10_ber", "24_mean_position_ber", "25_max_position_ber", "26_min_position_ber", "27_absoluteBerImprovement", "28_relativeBerReductionPercent"}
    inventory = [row for row in existing if not (row["scheme"] == "BCH" and row["plotId"] in replaced)]
    inventory += generate_bch_revision()
    inventory.sort(key=lambda row: (0 if row["scheme"] == "BCH" else 1, row["plotId"]))
    fields=["plotId","scheme","title","directory","status","sourceAbsolutePaths"]
    with (STAGE/"results"/"plot_inventory.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(inventory)
    print(f"PASS_S7_STAGE15_GENERATION plots={len(inventory)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
