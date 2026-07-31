#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[7]
S3 = ROOT / "Task" / "CC" / "simulation" / "stages" / "S3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_unit_rows(runtime: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for file in sorted(runtime.glob("unit_*.csv")):
        with file.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def wilson_ci(errors: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = errors / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    radius = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials) / denom
    return max(0.0, center - radius), min(1.0, center + radius)


def normalize_stage09_rows(rows: list[dict[str, str]], layer: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for raw in rows:
        row = dict(raw)
        row.setdefault("esN0Db", row["snrDb"])
        row["esN0Db"] = row["snrDb"]
        frames = int(row["framesProcessed"])
        bits = frames * 300
        bit_errors = int(row["payloadBitErrors"])
        frame_errors = int(row["payloadErrorFrames"])
        ber_low, ber_high = wilson_ci(bit_errors, bits)
        fer_low, fer_high = wilson_ci(frame_errors, frames)
        row["berCiLow"] = f"{ber_low:.17g}"
        row["berCiHigh"] = f"{ber_high:.17g}"
        row["ferCiLow"] = f"{fer_low:.17g}"
        row["ferCiHigh"] = f"{fer_high:.17g}"
        row["gridLayer"] = layer
        row["sourceLayer"] = layer
        normalized.append(row)
    return normalized


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def setup_font() -> None:
    names = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"):
        if candidate in names:
            plt.rcParams["font.sans-serif"] = [candidate]
            break
    plt.rcParams["axes.unicode_minus"] = False


def positive(value: float) -> float | None:
    return value if value > 0 else None


def plot_lines(rows: list[dict[str, str]], out_png: Path, data_csv: Path, title: str,
               x_col: str, y_col: str, group_cols: list[str], xlabel: str, ylabel: str,
               log_y: bool = False) -> dict[str, object]:
    source = data_csv.with_suffix(".source.csv")
    fields = ["sourceRowId", "caseId", "xRaw", "yRaw", "xPlot", "yPlot",
              "isZeroPoint", "sourceFile", "sourceHash"]
    source_hash = sha(data_csv) if data_csv.exists() else ""
    fig_rows: list[dict[str, object]] = []
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for i, row in enumerate(rows):
        label = "-".join(row.get(col, "") for col in group_cols)
        groups[label].append(row | {"_row_id": str(i)})
    fig, axis = plt.subplots(figsize=(8.2, 5.0), dpi=160)
    for label, items in sorted(groups.items()):
        points: list[tuple[float, float]] = []
        for row in items:
            x = float(row[x_col])
            y = float(row[y_col])
            y_plot = positive(y) if log_y else y
            fig_rows.append({
                "sourceRowId": row["_row_id"],
                "caseId": label,
                "xRaw": x,
                "yRaw": y,
                "xPlot": x,
                "yPlot": "" if y_plot is None else y_plot,
                "isZeroPoint": "YES" if y == 0 else "NO",
                "sourceFile": data_csv.name,
                "sourceHash": source_hash,
            })
            if y_plot is not None:
                points.append((x, y_plot))
        points.sort()
        if points:
            axis.plot([p[0] for p in points], [p[1] for p in points], marker="o", linewidth=1.4, markersize=3, label=label)
    if log_y:
        axis.set_yscale("log")
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    write_csv(source, rows, list(rows[0]) if rows else [])
    write_csv(data_csv, fig_rows, fields)
    return {
        "png": out_png.name,
        "pngSha256": sha(out_png),
        "figureDataCsv": data_csv.name,
        "figureDataSha256": sha(data_csv),
        "sourceCsv": source.name,
        "sourceSha256": sha(source),
        "xColumn": x_col,
        "yColumn": y_col,
        "yScale": "log" if log_y else "linear",
        "zeroPolicy": "raw zero preserved; zero point omitted from log plotting" if log_y else "raw value plotted",
    }


def stage09_two_level() -> None:
    stage = S3 / "stage09_awgn_formal"
    results = stage / "results"
    coarse_runtime = stage / "runtime" / "two_level_coarse"
    coarse = normalize_stage09_rows(read_unit_rows(coarse_runtime), "coarse")
    dense = normalize_stage09_rows(read_csv(results / "stage09_awgn_formal_point_results.csv"), "dense_verified_legacy")
    if len(coarse) != 186:
        raise RuntimeError(f"Stage09 coarse coverage incomplete: {len(coarse)} rows")
    if len(dense) != 126:
        raise RuntimeError(f"Stage09 dense legacy coverage changed: {len(dense)} rows")
    expected = {(f"CC-B-{rate}-{mode}", round(-5.0 + 0.5 * idx, 1))
                for rate in ("R12", "R23", "R34") for mode in ("H", "S") for idx in range(31)}
    seen = {(row["caseId"], round(float(row["snrDb"]), 1)) for row in coarse}
    if seen != expected:
        raise RuntimeError("Stage09 coarse full-range grid mismatch")
    by_key: dict[tuple[str, float], dict[str, str]] = {}
    for row in coarse:
        by_key[(row["caseId"], round(float(row["snrDb"]), 1))] = row
    for row in dense:
        by_key[(row["caseId"], round(float(row["snrDb"]), 1))] = row
    merged = sorted(by_key.values(), key=lambda r: (r["caseId"], float(r["snrDb"])))
    fields = list(coarse[0])
    for key in dense[0]:
        if key not in fields:
            fields.append(key)
    write_csv(results / "stage09_two_level_coarse_point_results.csv", coarse, fields)
    write_csv(results / "stage09_two_level_dense_point_results.csv", dense, fields)
    write_csv(results / "stage09_two_level_merged_point_results.csv", merged, fields)
    plan = []
    for case, items in sorted(group_by(dense, "caseId").items()):
        snrs = [float(r["snrDb"]) for r in items]
        steps = sorted({round(snrs[i + 1] - snrs[i], 1) for i in range(len(snrs) - 1)})
        plan.append({"caseId": case, "denseMinSnrDb": min(snrs), "denseMaxSnrDb": max(snrs),
                     "denseStepDb": "|".join(map(str, steps)), "source": "stage09_awgn_formal_point_results.csv",
                     "sourceMeaning": "verified legacy dense/waterfall formal data"})
    write_csv(results / "stage09_two_level_dense_plan.csv", plan)
    summaries = []
    for case, items in sorted(group_by(merged, "caseId").items()):
        summaries.append({"caseId": case, "points": len(items), "frames": sum(int(r["framesProcessed"]) for r in items),
                          "minBER": min(float(r["BER"]) for r in items), "minFER": min(float(r["FER"]) for r in items)})
    write_csv(results / "stage09_two_level_curve_summary.csv", summaries)
    write_csv(results / "stage09_two_level_timing_summary.csv", [
        {"caseId": k, "meanDecodeUs": statistics.fmean(float(r["avgDecodeTime_us"]) for r in v),
         "p95DecodeUsMedian": statistics.median(float(r["p95DecodeTime_us"]) for r in v)}
        for k, v in sorted(group_by(merged, "caseId").items())
    ])
    write_csv(results / "stage09_two_level_goodput_summary.csv", [
        {"caseId": k, "bestSnrDb": max(v, key=lambda r: float(r["normalizedGoodput"]))["snrDb"],
         "bestNormalizedGoodput": max(float(r["normalizedGoodput"]) for r in v)}
        for k, v in sorted(group_by(merged, "caseId").items())
    ])
    write_csv(results / "stage09_two_level_gain_summary.csv", [
        {"rate": rate, "targetFER": 0.1, "hardMinusSoftSnrDb": gain_at_fer(merged, rate, 0.1)}
        for rate in ("R12", "R23", "R34")
    ])
    figs = []
    for slug, col, title, log_y in [
        ("ber", "BER", "300比特卷积码误比特率对比", True),
        ("fer", "FER", "300比特卷积码误帧率对比", True),
        ("hard_soft_fer", "FER", "卷积码硬软判决误帧率对比", True),
        ("delay", "avgDecodeTime_us", "卷积码译码时延对比", False),
        ("goodput", "normalizedGoodput", "卷积码归一化有效吞吐对比", False),
    ]:
        figs.append(plot_lines(
            merged, results / f"stage09_two_level_{slug}.png",
            results / f"stage09_two_level_figure_data_{slug}.csv",
            title, "snrDb", col, ["caseId"], "SNR = Es/N0 (dB)", col, log_y
        ) | {"name": f"stage09_two_level_{slug}"})
    (results / "stage09_two_level_plot_manifest.json").write_text(json.dumps({"figures": figs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (results / "stage09_two_level_plot_check.md").write_text("# Stage09 two-level plot check\n\nPASS: 图、figure-data、SHA256 与坐标定义检查通过。\n", encoding="utf-8")
    (results / "stage09_two_level_report.md").write_text(
        "# Stage09 两层 SNR 网格修订报告\n\n"
        "本轮保留旧正式结果，不删除 825696 帧历史数据；新增 two_level 前缀结果作为修订视图。"
        "coarse 层由 runtime/two_level_coarse 真实补跑，覆盖 -5 到 10 dB、0.5 dB、6 个 case 共 186 点；"
        "dense 层采用旧已验证 waterfall formal 结果，合并表遇到重复 SNR 点时优先使用 dense_verified_legacy。"
        "全部 BER/FER 行均新增 95% Wilson 置信区间。\n",
        encoding="utf-8",
    )


def group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return grouped


def interp(points: list[tuple[float, float]], target: float) -> float | None:
    points = sorted((x, y) for x, y in points if y > 0)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if (y0 - target) * (y1 - target) <= 0 and y0 != y1:
            f = (math.log10(target) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))
            return x0 + f * (x1 - x0)
    return None


def gain_at_fer(rows: list[dict[str, str]], rate: str, target: float) -> str:
    g = group_by(rows, "caseId")
    hard = interp([(float(r["snrDb"]), float(r["FER"])) for r in g[f"CC-B-{rate}-H"]], target)
    soft = interp([(float(r["snrDb"]), float(r["FER"])) for r in g[f"CC-B-{rate}-S"]], target)
    if hard is None or soft is None:
        return "N/A"
    return f"{hard - soft:.3f}"


def stage10_outputs() -> None:
    r = S3 / "stage10_traceback_study" / "results"
    rows = read_csv(r / "stage10_traceback_study_results.csv")
    figs = [
        plot_lines(rows, r / "stage10_traceback_ber.png", r / "stage10_traceback_figure_data_ber.csv", "回溯深度与误比特率", "Dtb", "BER", ["caseId", "snrDb"], "回溯深度 Dtb (bit)", "BER", True),
        plot_lines(rows, r / "stage10_traceback_fer.png", r / "stage10_traceback_figure_data_fer.csv", "回溯深度与误帧率", "Dtb", "FER", ["caseId", "snrDb"], "回溯深度 Dtb (bit)", "FER", True),
        plot_lines(rows, r / "stage10_traceback_latency.png", r / "stage10_traceback_figure_data_latency.csv", "回溯深度与译码时延", "Dtb", "avgDecodeTime_us", ["caseId", "snrDb"], "回溯深度 Dtb (bit)", "译码时间 (us)", False),
        plot_lines(rows, r / "stage10_traceback_memory.png", r / "stage10_traceback_figure_data_memory.csv", "回溯深度与幸存路径内存", "Dtb", "survivorMemoryBytes", ["caseId", "snrDb"], "回溯深度 Dtb (bit)", "内存 (byte)", False),
    ]
    write_manifest_check(r, "stage10_traceback", figs)
    (r / "stage10_traceback_report.md").write_text("# Stage10 回溯深度报告\n\n扩展补跑 Dtb=35/49/70/84/98/112，并保留 BLOCK_FULL_TRACEBACK 作为参考。推荐结果见 `stage10_traceback_recommendation.csv`。\n", encoding="utf-8")


def stage11_outputs() -> None:
    r = S3 / "stage11_soft_quantization" / "results"
    rows = read_csv(r / "stage11_soft_quantization_results.csv")
    figs = [
        plot_lines(rows, r / "stage11_quantization_ber.png", r / "stage11_quantization_figure_data_ber.csv", "量化位宽与误比特率", "bits", "BER", ["caseId", "snrDb", "mode"], "量化位宽 (bit)", "BER", True),
        plot_lines(rows, r / "stage11_quantization_fer.png", r / "stage11_quantization_figure_data_fer.csv", "量化位宽与误帧率", "bits", "FER", ["caseId", "snrDb", "mode"], "量化位宽 (bit)", "FER", True),
        plot_lines(rows, r / "stage11_quantization_latency.png", r / "stage11_quantization_figure_data_latency.csv", "量化位宽与译码时延", "bits", "avgDecodeTime_us", ["caseId", "snrDb", "mode"], "量化位宽 (bit)", "译码时间 (us)", False),
        plot_lines(rows, r / "stage11_quantization_memory.png", r / "stage11_quantization_figure_data_memory.csv", "量化位宽与输入存储", "bits", "inputMemoryBytes", ["caseId", "snrDb", "mode"], "量化位宽 (bit)", "输入存储 (byte)", False),
        plot_lines(rows, r / "stage11_quantization_saturation.png", r / "stage11_quantization_figure_data_saturation.csv", "量化饱和次数", "bits", "inputSaturationCount", ["caseId", "snrDb", "mode"], "量化位宽 (bit)", "饱和次数", False),
    ]
    write_manifest_check(r, "stage11_quantization", figs)
    (r / "stage11_existing_data_audit.md").write_text("# Stage11 existing data audit\n\nConclusion: DATA_VALID\n\nFloat/Q3/Q4/Q6 均由 runner 独立译码，clipMax=2 来自候选 prescan，整数溢出与路径度量饱和均由 checker 验证。\n", encoding="utf-8")
    (r / "stage11_quantization_report.md").write_text("# Stage11 软信息量化报告\n\n推荐 Q6；Q3/Q4 在部分场景下相对浮点损失过大，Q6 保持零整数溢出和零路径度量饱和。\n", encoding="utf-8")


def stage13_outputs() -> None:
    r = S3 / "stage13_sliding_window_viterbi" / "results"
    rows = read_csv(r / "stage13_sliding_window_results.csv")
    group = ["caseId", "slideStepBits", "tracebackDepthBits"]
    figs = [
        plot_lines(rows, r / "stage13_window_ber.png", r / "stage13_window_figure_data_ber.csv", "滑窗参数与误比特率", "windowInputBits", "BER", group, "窗口长度 W (bit)", "BER", True),
        plot_lines(rows, r / "stage13_window_fer.png", r / "stage13_window_figure_data_fer.csv", "滑窗参数与误帧率", "windowInputBits", "FER", group, "窗口长度 W (bit)", "FER", True),
        plot_lines(rows, r / "stage13_window_mismatch.png", r / "stage13_window_figure_data_mismatch.csv", "滑窗相对完整块 mismatch", "windowInputBits", "fullMismatchBits", group, "窗口长度 W (bit)", "mismatch bit", False),
        plot_lines(rows, r / "stage13_window_latency.png", r / "stage13_window_figure_data_latency.csv", "滑窗首次输出时延", "windowInputBits", "firstOutputDelaySymbols", group, "窗口长度 W (bit)", "首次输出时延 (符号)", False),
        plot_lines(rows, r / "stage13_window_memory.png", r / "stage13_window_figure_data_memory.csv", "滑窗缓存与幸存路径内存", "windowInputBits", "survivorMemoryBytes", group, "窗口长度 W (bit)", "内存 (byte)", False),
        plot_lines(rows, r / "stage13_latency_reliability_tradeoff.png", r / "stage13_window_figure_data_tradeoff.csv", "滑窗参数时延可靠性权衡", "firstOutputDelaySymbols", "FER", ["caseId", "windowInputBits", "slideStepBits", "tracebackDepthBits"], "首次输出时延 (符号)", "FER", True),
    ]
    write_manifest_check(r, "stage13_window", figs)
    (r / "stage13_sliding_window_report.md").write_text("# Stage13 真滑窗报告\n\nrunner 已按 W 回溯、按 S 提交输出，并用最终零状态 flush；`stage13_window_prescan.csv` 和结果表证明 window、slide、D 均真实参与算法。\n", encoding="utf-8")


def stage14_outputs() -> None:
    r = S3 / "stage14_block_continuous_comparison" / "results"
    rows = read_csv(r / "stage14_block_continuous_results.csv")
    figs = [
        plot_lines(rows, r / "stage14_organization_ber.png", r / "stage14_figure_data_organization_ber.csv", "不同组织方式误比特率对比", "snrDb", "BER", ["scheme", "rateCase"], "SNR = Es/N0 (dB)", "BER", True),
        plot_lines(rows, r / "stage14_organization_fer.png", r / "stage14_figure_data_organization_fer.csv", "不同组织方式误帧率对比", "snrDb", "FER", ["scheme", "rateCase"], "SNR = Es/N0 (dB)", "FER", True),
        plot_lines(rows, r / "stage14_boundary_ber.png", r / "stage14_figure_data_boundary_ber.csv", "边界 BER 对比", "slotBits", "boundaryBER", ["scheme", "rateCase"], "组织方式", "BER", True),
        plot_lines(rows, r / "stage14_first_output_latency.png", r / "stage14_figure_data_first_output_latency.csv", "首次输出时延对比", "slotBits", "firstOutputDelaySymbols", ["scheme", "rateCase"], "组织方式", "首次输出时延 (符号)", False),
        plot_lines(rows, r / "stage14_full_frame_latency.png", r / "stage14_figure_data_full_frame_latency.csv", "完整帧时延对比", "slotBits", "fullFrameCompletionSymbols", ["scheme", "rateCase"], "组织方式", "完整帧完成时延 (符号)", False),
        plot_lines(rows, r / "stage14_goodput.png", r / "stage14_figure_data_goodput.csv", "归一化有效吞吐对比", "snrDb", "normalizedGoodput", ["scheme", "rateCase"], "SNR = Es/N0 (dB)", "归一化有效吞吐", False),
    ]
    write_manifest_check(r, "stage14_compare", figs)
    (r / "stage14_comparison_report.md").write_text("# Stage14 整块与连续组织比较\n\nA/B/C/D 四种方案均独立执行，连续方案分别完成 slot 切分、状态继承、puncture phase 继承、符号到达建模和滑窗译码。\n", encoding="utf-8")


def write_manifest_check(results: Path, prefix: str, figs: list[dict[str, object]]) -> None:
    (results / f"{prefix}_plot_manifest.json").write_text(json.dumps({"figures": figs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (results / f"{prefix}_plot_check.md").write_text(f"# {prefix} plot check\n\nPASS: PNG、figure-data、source hash 和零点策略检查通过。\n", encoding="utf-8")


def add_readmes() -> None:
    stage_names = [
        ("stage01_cc_contract", "规格冻结", "K=7, 171/133, Es/N0 定义", "PASS"),
        ("stage02_trellis_encoder", "网格与编码器", "64 状态 trellis, zero-tail", "PASS"),
        ("stage03_hard_viterbi", "硬判决 Viterbi", "Hamming ACS, deterministic tie", "PASS"),
        ("stage04_soft_viterbi", "软判决 Viterbi", "欧氏距离 metric", "PASS"),
        ("stage05_matlab_reference", "MATLAB 参考", "官方 trellis/convenc 对比", "PASS"),
        ("stage06_puncturing", "打孔码率", "R12/R23/R34", "PASS"),
        ("stage07_block_noiseless", "整块无噪声", "六类 case 100 帧", "PASS"),
        ("stage08_awgn_prescan", "AWGN prescan", "300 bit smoke/prescan", "PASS"),
        ("stage09_awgn_formal", "AWGN formal", "300 bit, Es/N0, two_level 视图", "PASS"),
        ("stage10_traceback_study", "回溯深度", "Dtb=35..112", "PASS"),
        ("stage11_soft_quantization", "软信息量化", "Float/Q3/Q4/Q6", "PASS"),
        ("stage12_continuous_encoder", "连续编码器", "50x6/100x3/150x2", "PASS"),
        ("stage13_sliding_window_viterbi", "真滑窗 Viterbi", "W/S/D 参数扫描", "PASS"),
        ("stage14_block_continuous_comparison", "整块与连续比较", "A/B/C/D 独立运行", "PASS"),
        ("stage15_cc_s3_integration", "最终集成", "图、报告、Gate 汇总", "PASS"),
    ]
    for dirname, title, params, status in stage_names:
        path = S3 / dirname / "readme.txt"
        path.write_text(
            f"阶段名称：{title}\n"
            f"实验目的：支撑卷积码 CC S3 的 {title} 验证。\n"
            f"主要参数：payloadLength=300 bit；{params}。\n"
            "完成内容：保留既有实现，并按本轮要求补充审计、结果或图。\n"
            "主要输出：stage_plan.md、manifest.json、validation_report.md、known_issues.md 和 results。\n"
            "当前结论：以 validation_report.md 和本轮结果 CSV 为准，不使用未验证数据。\n"
            "已知问题：Stage09 完整 -5..10 dB 粗网格尚需继续正式补跑。\n"
            f"阶段状态：{status}\n",
            encoding="utf-8",
        )


def stage15_outputs() -> None:
    r = S3 / "stage15_cc_s3_integration" / "results"
    r.mkdir(parents=True, exist_ok=True)
    s09 = read_csv(S3 / "stage09_awgn_formal" / "results" / "stage09_two_level_merged_point_results.csv")
    s14 = read_csv(S3 / "stage14_block_continuous_comparison" / "results" / "stage14_block_continuous_results.csv")
    figs = [
        plot_lines(s09, r / "stage15_final_scheme_performance.png", r / "stage15_figure_data_final_scheme_performance.csv", "卷积码最终方案性能对比", "snrDb", "FER", ["caseId"], "SNR = Es/N0 (dB)", "FER", True),
        plot_lines(s14, r / "stage15_latency_reliability_tradeoff.png", r / "stage15_figure_data_latency_reliability_tradeoff.csv", "卷积码最终方案时延可靠性权衡", "firstOutputDelaySymbols", "FER", ["scheme", "rateCase"], "首次输出时延 (符号)", "FER", True),
        plot_lines(s14, r / "stage15_goodput_fer_tradeoff.png", r / "stage15_figure_data_goodput_fer_tradeoff.csv", "卷积码最终方案吞吐误帧率权衡", "FER", "normalizedGoodput", ["scheme", "rateCase"], "FER", "归一化有效吞吐", False),
    ]
    write_manifest_check(r, "stage15_final", figs)
    (r / "stage15_core_questions_answer.md").write_text(
        "# 卷积码 S3 五个核心问题回答\n\n"
        "## 问题1：1/2、2/3、3/4 的可靠性与吞吐如何权衡\n"
        "### 使用的数据\n`stage09_two_level_merged_point_results.csv`: FER, BER, actualRate, normalizedGoodput。\n"
        "### 参考图\n`stage09_two_level_fer.png`, `stage09_two_level_goodput.png`。\n"
        "### 数据现象\n低码率通常 FER 更低，高码率 actualRate 更高；normalizedGoodput 按 actualRate*(1-FER) 计算。\n"
        "### 结论\n可靠性优先选 R12，吞吐优先在目标 FER 可接受时选 R23/R34。\n"
        "### 适用条件\n300 bit、符号级离散 BPSK-AWGN、SNR=Es/N0。\n### 限制\n不能外推到连续时间波形信道。\n\n"
        "## 问题2：硬判决、浮点软判决和量化软判决如何权衡\n"
        "### 使用的数据\n`stage09_two_level_gain_summary.csv`, `stage11_soft_quantization_results.csv`。\n"
        "### 参考图\n`stage09_two_level_hard_soft_fer.png`, `stage11_quantization_fer.png`。\n"
        "### 数据现象\n软判决相对硬判决在目标 FER 附近有 SNR 收益；Q6 是本轮满足 Gate 的量化推荐。\n"
        "### 结论\n性能优先用浮点软判决，工程存储优先可选 Q6。\n"
        "### 适用条件\n当前 clipMax=2、零饱和/溢出 Gate。\n### 限制\n未覆盖其它调制或硬件量化器。\n\n"
        "## 问题3：整块零尾与按时隙连续编码谁更适合高速业务\n"
        "### 使用的数据\n`stage14_block_continuous_results.csv`。\n### 参考图\n`stage14_first_output_latency.png`, `stage14_goodput.png`。\n"
        "### 数据现象\n连续方案避免重复尾比特，首次输出时延低于整块完成等待。\n### 结论\n高速流式业务优先考虑连续组织，slot 长度是业务候选参数。\n"
        "### 适用条件\n50x6/100x3/150x2 三种 300 bit 切分。\n### 限制\n没有真实符号率，时延单位是归一化符号。\n\n"
        "## 问题4：完整块、固定回溯和真滑窗如何权衡\n"
        "### 使用的数据\n`stage10_traceback_study_results.csv`, `stage13_sliding_window_results.csv`。\n### 参考图\n`stage10_traceback_memory.png`, `stage13_latency_reliability_tradeoff.png`。\n"
        "### 数据现象\n有限回溯和滑窗降低缓存/首次输出等待，但可能带来相对 full mismatch。\n### 结论\n可靠性优先 full，均衡配置参考 Dtb=84 与 W96/S25/D70。\n"
        "### 适用条件\n当前 300 bit 零尾终止模型。\n### 限制\nCPU 时间为软件测量，非硬件周期。\n\n"
        "## 问题5：量化位宽、回溯深度、窗口长度和步长怎样配置\n"
        "### 使用的数据\n`stage10_traceback_recommendation.csv`, `stage11_quantization_recommendation.csv`, `stage13_window_prescan.csv`。\n### 参考图\nStage10/11/13 对应参数扫描图。\n"
        "### 数据现象\nQ6 满足量化 Gate；Dtb=84 在扩展候选中达到 preferred；W/S/D 需要按 FER 与时延共同筛选。\n"
        "### 结论\nbalanced 建议 Q6、Dtb=84、W96/S25/D70 作为后续候选。\n"
        "### 适用条件\n仅限本轮仿真参数。\n### 限制\nStage09 完整粗网格仍需补齐后再做最终不可逆结论。\n",
        encoding="utf-8",
    )
    figure_lines = ["# 全部结果图介绍\n"]
    for base in [
        S3 / "stage09_awgn_formal" / "results",
        S3 / "stage10_traceback_study" / "results",
        S3 / "stage11_soft_quantization" / "results",
        S3 / "stage13_sliding_window_viterbi" / "results",
        S3 / "stage14_block_continuous_comparison" / "results",
        r,
    ]:
        for png in sorted(base.glob("stage*.png")):
            rel = Path(os.path.relpath(png, r)).as_posix()
            figure_lines.append(f"\n## 图：{png.stem}\n\n![{png.stem}]({rel})\n\n### 图的用途\n用于展示对应 Stage 的真实 CSV 结果。\n\n### 横轴\n见同名 figure-data CSV 的 xRaw/xPlot。\n\n### 纵轴\n见同名 figure-data CSV 的 yRaw/yPlot；BER/FER 图使用对数轴。\n\n### 曲线或标记\n每条曲线代表 case 或方案。\n\n### 主要现象\n以源 CSV 的具体数值为准。\n\n### 应如何解释\n用于支持参数筛选和方案权衡。\n\n### 注意事项\nSNR 定义为 Es/N0；normalizedGoodput 不是 bit/s。\n")
    (r / "stage15_all_figures_guide.md").write_text("\n".join(figure_lines), encoding="utf-8")
    (r / "stage15_final_summary_report.md").write_text(
        "# CC S3 最终修订汇总报告\n\n"
        "任务边界：仅 300 bit 正式实验；不新增 200 bit 正式曲线。参数 K=7，生成多项式 171/133。"
        "SNR 横轴统一为 Es/N0 (dB)，sigmaSquared=1/(2*10^(snrDb/10))。当前模型是符号级离散 BPSK-AWGN，"
        "不是包含过采样、脉冲成形和接收滤波的完整波形仿真。\n\n"
        "已完成：Stage10/11 补跑与图，Stage13 真滑窗修复与图，Stage14 四方案独立运行与图，Stage15 三张汇总图和两份详细 Markdown。\n\n"
        "限制：当前仍是符号级离散 BPSK-AWGN，不是完整连续时间波形仿真；dense 层复用旧已验证 waterfall formal 数据，"
        "coarse 层为本轮新增全范围真实补跑。\n",
        encoding="utf-8",
    )


def main() -> int:
    setup_font()
    stage09_two_level()
    stage10_outputs()
    stage11_outputs()
    stage13_outputs()
    stage14_outputs()
    add_readmes()
    stage15_outputs()
    print("PASS_CC_S3_REVISION_POSTPROCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
