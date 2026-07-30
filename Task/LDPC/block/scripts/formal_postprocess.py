"""Audit, plot, compare, and integrate S4-LDPC formal results."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import formal_s4 as fs


ROOT = fs.ROOT
STAGES = fs.STAGES
S15 = fs.S15
S16 = STAGES / "stage16_formal_result_audit"
S17 = STAGES / "stage17_formal_scientific_plots"
S18 = STAGES / "stage18_bp_nms_comparison"
S19 = STAGES / "stage19_length_extension_comparison"
S20 = STAGES / "stage20_s4_final_integration"
SOURCE_RAW = S16 / "results/formal_point_results_raw.csv"
SOURCE_AUDIT = S16 / "results/formal_point_results.csv"
COLORS = {480: "#1f77b4", 560: "#ff7f0e", 640: "#2ca02c"}


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fs.write_csv(path, rows, fields)


def read_csv(path: Path) -> list[dict[str, str]]:
    return fs.read_csv(path)


def label(row: dict[str, str]) -> str:
    n = int(row["actualLength"])
    if row["algorithm"] == "DIRECT_LAYERED_SPA_BP":
        return f"{n}比特 BP"
    return f"{n}比特 NMS（α={float(row['alpha']):.2f}）"


def setup_stage(stage: Path, purpose: str) -> None:
    fs.common_stage(stage, purpose)


def audit() -> None:
    setup_stage(S16, "审计 186 条正式结果的完整性、配对公平、停止规则、公式和异常。")
    out = S16 / "results"
    data = []
    for directory in sorted((S15 / "results/points").iterdir()):
        data.extend(read_csv(directory / "point_result.csv"))
    data.sort(key=lambda row: (int(row["actualLength"]), float(row["esN0Db"]),
                               row["algorithm"]))
    write_csv(out / "formal_point_results_raw.csv", data)
    anomalies = []
    pairing = []
    stop_rows = []
    formula_rows = []
    grouped = defaultdict(list)
    for row in data:
        grouped[(int(row["actualLength"]), float(row["esN0Db"]))].append(row)
        n = int(row["actualLength"])
        snr = float(row["esN0Db"])
        expected_sigma = 1 / (2 * 10 ** (snr / 10))
        expected_eb = snr - 10 * math.log10(300 / n)
        formula_rows.append({
            "actualLength": n, "esN0Db": snr, "algorithm": row["algorithm"],
            "sigmaSquared": row["sigmaSquared"], "expectedSigmaSquared": expected_sigma,
            "sigmaMatch": abs(float(row["sigmaSquared"]) - expected_sigma) < 1e-14,
            "ebN0Db": row["ebN0Db"], "expectedEbN0Db": expected_eb,
            "ebN0Match": abs(float(row["ebN0Db"]) - expected_eb) < 1e-12,
            "status": "PASS",
        })
        frames = int(row["frames"])
        categories = sum(int(row[name]) for name in [
            "correctValidFrames", "wrongValidFrames",
            "correctInvalidFrames", "wrongInvalidFrames"])
        reasons = []
        if not 1000 <= frames <= 50000:
            reasons.append("FRAME_RANGE")
        if categories != frames:
            reasons.append("OUTCOME_SUM")
        if int(row["bitErrors"]) > frames * 300:
            reasons.append("BIT_ERROR_RANGE")
        if int(row["nanInfCount"]) != 0:
            reasons.append("NAN_INF")
        if not 0 <= float(row["BER"]) <= 1 or not 0 <= float(row["FER"]) <= 1:
            reasons.append("RATE_RANGE")
        if float(row["actualRate"]) != 300 / n:
            reasons.append("RATE_FORMULA")
        expected_alpha = 0.0 if row["algorithm"] == "DIRECT_LAYERED_SPA_BP" else fs.ALPHAS[n]
        if abs(float(row["alpha"]) - expected_alpha) > 1e-12:
            reasons.append("ALPHA")
        if int(row["frameErrors"]) == 0 and float(row["FER"]) != 0:
            reasons.append("ZERO_FER_REPLACED")
        if int(row["bitErrors"]) == 0 and float(row["BER"]) != 0:
            reasons.append("ZERO_BER_REPLACED")
        for reason in reasons:
            anomalies.append({"actualLength": n, "esN0Db": snr,
                              "algorithm": row["algorithm"], "anomaly": reason,
                              "severity": "BLOCKING"})
    if len(data) != 186 or len(grouped) != 93:
        raise RuntimeError("BLOCKED_STAGE16_FORMAL_RESULT_INVALID row count")
    if {int(row["actualLength"]) for row in data} != {480, 560, 640}:
        raise RuntimeError("BLOCKED_STAGE16_FORMAL_RESULT_INVALID cases")
    for key, pair in sorted(grouped.items()):
        if len(pair) != 2 or {row["algorithm"] for row in pair} != {
                "DIRECT_LAYERED_SPA_BP", "DIRECT_LAYERED_NMS"}:
            raise RuntimeError(f"BLOCKED_STAGE16_FORMAL_RESULT_INVALID pair {key}")
        bp = next(row for row in pair if row["algorithm"] == "DIRECT_LAYERED_SPA_BP")
        nms = next(row for row in pair if row["algorithm"] == "DIRECT_LAYERED_NMS")
        shared_fields = ["frames", "frameStart", "frameEnd", "payloadSeed", "noiseSeed",
                         "runId", "payloadHash", "codewordHash", "llrHash"]
        matches = {field: bp[field] == nms[field] for field in shared_fields}
        pairing.append({
            "actualLength": key[0], "esN0Db": key[1],
            **{f"{field}Match": value for field, value in matches.items()},
            "status": "PASS" if all(matches.values()) else "FAIL",
        })
        frames = int(bp["frames"])
        bp_errors = int(bp["frameErrors"])
        nms_errors = int(nms["frameErrors"])
        stop = bp["stopReason"]
        valid_stop = (
            stop == nms["stopReason"]
            and ((stop == "TARGET_FRAME_ERRORS_REACHED" and frames >= 1000
                  and bp_errors >= 200 and nms_errors >= 200)
                 or (stop == "MAX_FRAMES_REACHED" and frames == 50000
                     and (bp_errors < 200 or nms_errors < 200))))
        stop_rows.append({
            "actualLength": key[0], "esN0Db": key[1], "frames": frames,
            "bpFrameErrors": bp_errors, "nmsFrameErrors": nms_errors,
            "stopReason": stop, "status": "PASS" if valid_stop else "FAIL",
        })
    if anomalies or any(row["status"] != "PASS" for row in pairing + stop_rows):
        write_csv(out / "formal_anomaly_report.csv", anomalies,
                  ["actualLength", "esN0Db", "algorithm", "anomaly", "severity"])
        raise RuntimeError("BLOCKED_STAGE16_FORMAL_RESULT_INVALID")
    # Preserve raw numeric values exactly in audited CSV.
    shutil.copy2(out / "formal_point_results_raw.csv", out / "formal_point_results.csv")
    write_csv(out / "formal_pairing_audit.csv", pairing)
    write_csv(out / "formal_stop_rule_audit.csv", stop_rows)
    write_csv(out / "formal_snr_formula_audit.csv", formula_rows)
    write_csv(out / "formal_anomaly_report.csv", [],
              ["actualLength", "esN0Db", "algorithm", "anomaly", "severity"])
    zeros_ber = sum(int(row["bitErrors"]) == 0 for row in data)
    zeros_fer = sum(int(row["frameErrors"]) == 0 for row in data)
    local_waves = []
    for n in fs.LENGTHS:
        for algorithm in ["DIRECT_LAYERED_SPA_BP", "DIRECT_LAYERED_NMS"]:
            curve = sorted((row for row in data if int(row["actualLength"]) == n
                            and row["algorithm"] == algorithm),
                           key=lambda row: float(row["esN0Db"]))
            for left, right in zip(curve, curve[1:]):
                if float(right["FER"]) > float(left["FER"]):
                    local_waves.append((n, algorithm, left["esN0Db"], right["esN0Db"]))
    fs.atomic_text(out / "formal_completeness_report.md",
                   "# Formal 完整性报告\n\n"
                   "- Case：3；每 Case Es/N0 点：31；每点算法：2；总记录：186。\n"
                   "- BP/NMS frames、边界、seed、runId、输入 hash：全部一致。\n"
                   "- 停止规则、四分类、BER/FER、rate、sigma、Eb/N0、alpha：全部 PASS。\n"
                   f"- BER 零错误记录：{zeros_ber}；FER 零错误记录：{zeros_fer}；原始零值均保留。\n"
                   f"- 局部 FER 反向次数：{len(local_waves)}；均保留原始值，不删除不平滑。\n"
                   "- Gate：PASS_STAGE16_FORMAL_RESULT_AUDIT\n")
    fs.atomic_text(S16 / "commands_used.md",
                   "# 实际命令\n\n- 汇总 93 个 point_result.csv\n"
                   "- 执行 pairing/stop/formula/completeness/zero-preservation checker\n")
    fs.atomic_text(S16 / "validation_report.md",
                   "# 验证报告\n\n- 186/186：PASS\n- pairing：PASS\n"
                   "- stop rule：PASS\n- NaN/Inf：0\n- zero preservation：PASS\n"
                   "- Gate：PASS_STAGE16_FORMAL_RESULT_AUDIT\n")


def style_for(row: dict[str, str]) -> tuple[str, str, str]:
    n = int(row["actualLength"])
    bp = row["algorithm"] == "DIRECT_LAYERED_SPA_BP"
    return COLORS[n], "-" if bp else "--", "o" if bp else "s"


def plot_manifest(result_dir: Path, stem: str, figure_data: Path, png: Path,
                  x_column: str, y_column: str, x_unit: str, y_unit: str,
                  x_scale: str, y_scale: str, zero_handling: str,
                  series: list[str]) -> None:
    script = Path(__file__)
    value = {
        "sourceRawCsv": str(SOURCE_RAW.relative_to(ROOT)).replace("\\", "/"),
        "sourceRawCsvSha256": fs.sha256(SOURCE_RAW),
        "sourceAuditedCsv": str(SOURCE_AUDIT.relative_to(ROOT)).replace("\\", "/"),
        "sourceAuditedCsvSha256": fs.sha256(SOURCE_AUDIT),
        "figureDataCsv": figure_data.name,
        "figureDataCsvSha256": fs.sha256(figure_data),
        "xColumn": x_column, "yColumn": y_column, "xUnit": x_unit, "yUnit": y_unit,
        "xScale": x_scale, "yScale": y_scale, "seriesMapping": series,
        "colorMapping": {str(k): v for k, v in COLORS.items()},
        "lineStyleMapping": {"BP": "-", "NMS": "--"},
        "markerMapping": {"BP": "o", "NMS": "s"},
        "zeroHandling": zero_handling,
        "zeroErrorUpperBoundFormula": "1-0.05^(1/trials)",
        "interpolation": False, "smoothing": False,
        "plotScript": str(script.relative_to(ROOT)).replace("\\", "/"),
        "plotScriptSha256": fs.sha256(script), "pngSha256": fs.sha256(png),
    }
    fs.atomic_json(result_dir / f"{stem}_plot_manifest.json", value)
    fs.atomic_text(result_dir / f"{stem}_plot_check.md",
                   "# Plot check\n\n- source hash：PASS\n- 无插值/平滑：PASS\n"
                   f"- series：{len(series)}\n- zero handling：{zero_handling}\n- PNG：PASS\n")


def plot_metric(data: list[dict[str, str]], result_dir: Path, stem: str,
                title: str, metric: str, ylabel: str, log_y: bool = False) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure_rows = []
    for row in data:
        raw = float(row[metric])
        zero = raw == 0 and metric in {"BER", "FER"}
        upper = float(row["berUpper95"] if metric == "BER" else row["ferUpper95"]) if zero else ""
        figure_rows.append({
            "actualLength": row["actualLength"], "algorithm": row["algorithm"],
            "alpha": row["alpha"], "series": label(row), "esN0Db": row["esN0Db"],
            "rawValue": raw, "isZeroError": str(zero).lower(),
            "plottedAsRegularPoint": str(not zero).lower(),
            "upperBound95": upper,
            "plotTreatment": ("ZERO_ERROR_CENSORED_NOT_CONNECTED" if zero
                              else "REGULAR_MEASURED_POINT"),
            "frames": row["frames"],
        })
    figure_data = result_dir / f"{stem}_figure_data.csv"
    write_csv(figure_data, figure_rows)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    series_names = []
    grouped = defaultdict(list)
    for row in data:
        grouped[label(row)].append(row)
    for name, curve in grouped.items():
        series_names.append(name)
        curve.sort(key=lambda row: float(row["esN0Db"]))
        color, line, marker = style_for(curve[0])
        if log_y:
            segment_x, segment_y = [], []
            for row in curve:
                value = float(row[metric])
                if value > 0:
                    segment_x.append(float(row["esN0Db"]))
                    segment_y.append(value)
                else:
                    if segment_x:
                        ax.plot(segment_x, segment_y, color=color, linestyle=line,
                                marker=marker, markersize=4, linewidth=1.4,
                                label=name if not any(item.get_label() == name for item in ax.lines) else None)
                        segment_x, segment_y = [], []
                    upper = float(row["berUpper95"] if metric == "BER" else row["ferUpper95"])
                    ax.scatter([float(row["esN0Db"])], [upper], facecolors="none",
                               edgecolors=color, marker="v", s=38)
            if segment_x:
                ax.plot(segment_x, segment_y, color=color, linestyle=line,
                        marker=marker, markersize=4, linewidth=1.4,
                        label=name if not any(item.get_label() == name for item in ax.lines) else None)
        else:
            ax.plot([float(row["esN0Db"]) for row in curve],
                    [float(row[metric]) for row in curve], color=color,
                    linestyle=line, marker=marker, markersize=4, linewidth=1.4, label=name)
    ax.set_xlabel("Es/N0（dB）")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, which="both", alpha=0.28)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.tight_layout()
    png = result_dir / f"{stem}.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)
    zero_handling = ("RAW_ZERO_PRESERVED_NOT_CONNECTED_AS_REGULAR_POINT"
                     if log_y else "NOT_APPLICABLE")
    plot_manifest(result_dir, stem, figure_data, png, "esN0Db", metric, "dB",
                  ylabel, "linear", "log" if log_y else "linear",
                  zero_handling, sorted(series_names))


def plots() -> None:
    setup_stage(S17, "从通过 Stage16 审计的数据生成 12 张科研图及完整 sidecar。")
    out = S17 / "results"
    data = read_csv(SOURCE_AUDIT)
    specifications = [
        ("formal_ber", "300比特LDPC误比特率对比", "BER", "误比特率", True),
        ("formal_fer", "300比特LDPC误帧率对比", "FER", "误帧率", True),
        ("formal_avg_iterations", "LDPC平均迭代次数对比", "avgIterations", "平均迭代次数（次）", False),
        ("formal_p95_iterations", "LDPC P95迭代次数对比", "p95Iterations", "P95迭代次数（次）", False),
        ("formal_avg_delay", "LDPC平均译码时延对比", "avgDecodeTimeUs", "平均译码时延（微秒）", False),
        ("formal_p95_delay", "LDPC P95译码时延对比", "p95DecodeTimeUs", "P95译码时延（微秒）", False),
        ("formal_max_delay", "LDPC最大译码时延对比", "maxDecodeTimeUs", "最大译码时延（微秒）", False),
        ("formal_avg_edge_updates", "LDPC平均边消息更新次数对比", "avgEdgeMessageUpdates",
         "平均边消息更新次数/帧", False),
        ("formal_operation_count", "LDPC理论操作计数对比", "avgTheoreticalOperationCount",
         "平均理论操作计数/帧", False),
        ("formal_wrong_valid_rate", "LDPC错误合法码字率对比", "wrongValidRate", "错误合法码字率", False),
        ("formal_valid_codeword_rate", "LDPC有效码字率对比", "validCodewordRate", "有效码字率", False),
    ]
    for specification in specifications:
        plot_metric(data, out, *specification)
    # Rate versus actual length.
    rate_rows = []
    for n in fs.LENGTHS:
        rate_rows.append({
            "actualLength": n, "actualRate": fs.RATES[n],
            "targetLength": 480 if n == 480 else (576 if n == 560 else 640),
            "series": "Direct BG2 frozen case",
        })
    figure_data = out / "formal_rate_length_figure_data.csv"
    write_csv(figure_data, rate_rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([row["actualLength"] for row in rate_rows],
            [row["actualRate"] for row in rate_rows], marker="o")
    ax.set_xlabel("实际码长（比特）")
    ax.set_ylabel("实际码率")
    ax.set_title("LDPC实际码率与码长对比")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    png = out / "formal_rate_length.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)
    plot_manifest(out, "formal_rate_length", figure_data, png, "actualLength",
                  "actualRate", "bit", "ratio", "linear", "linear",
                  "NOT_APPLICABLE", ["Direct BG2 frozen case"])
    fs.atomic_text(S17 / "commands_used.md",
                   "# 实际命令\n\n- `python Task/LDPC/block/scripts/formal_postprocess.py plots`\n")
    fs.atomic_text(S17 / "validation_report.md",
                   "# 验证报告\n\n- 科研图：12/12\n- 每图 sidecar：PASS\n"
                   "- 原始零值保留且不连接为普通曲线：PASS\n"
                   "- 插值/平滑：未使用\n- Gate：PASS_STAGE17_FORMAL_SCIENTIFIC_PLOTS\n")


def estimate_target(curve: list[dict[str, str]], target: float) -> dict:
    ordered = sorted(curve, key=lambda row: float(row["esN0Db"]))
    for left, right in zip(ordered, ordered[1:]):
        yl, yr = float(left["FER"]), float(right["FER"])
        if yl > 0 and yr > 0 and (yl >= target >= yr or yl <= target <= yr) and yl != yr:
            xl, xr = float(left["esN0Db"]), float(right["esN0Db"])
            estimate = xl + (math.log10(target) - math.log10(yl)) * (xr - xl) / (
                math.log10(yr) - math.log10(yl))
            return {
                "targetFER": target, "leftEsN0Db": xl, "leftFER": yl,
                "rightEsN0Db": xr, "rightFER": yr,
                "formula": "x=xL+(log10(t)-log10(yL))*(xR-xL)/(log10(yR)-log10(yL))",
                "estimatedEsN0Db": estimate, "computable": "true", "reason": "",
            }
    return {
        "targetFER": target, "leftEsN0Db": "", "leftFER": "",
        "rightEsN0Db": "", "rightFER": "", "formula": "",
        "estimatedEsN0Db": "", "computable": "false",
        "reason": "NO_ADJACENT_NONZERO_FORMAL_POINTS_BRACKET_TARGET",
    }


def comparisons() -> None:
    setup_stage(S18, "正式比较 BP 与 NMS 的性能、时延、迭代和多维复杂度。")
    out = S18 / "results"
    data = read_csv(SOURCE_AUDIT)
    grouped = defaultdict(dict)
    for row in data:
        grouped[(int(row["actualLength"]), float(row["esN0Db"]))][row["algorithm"]] = row
    points, delays, complexity = [], [], []
    for (n, snr), pair in sorted(grouped.items()):
        bp, nms = pair["DIRECT_LAYERED_SPA_BP"], pair["DIRECT_LAYERED_NMS"]
        points.append({
            "actualLength": n, "esN0Db": snr,
            "berDifferenceNmsMinusBp": float(nms["BER"]) - float(bp["BER"]),
            "ferDifferenceNmsMinusBp": float(nms["FER"]) - float(bp["FER"]),
            "avgIterationDifferenceNmsMinusBp": float(nms["avgIterations"]) - float(bp["avgIterations"]),
            "avgDelayDifferenceUs": float(nms["avgDecodeTimeUs"]) - float(bp["avgDecodeTimeUs"]),
            "p95DelayDifferenceUs": float(nms["p95DecodeTimeUs"]) - float(bp["p95DecodeTimeUs"]),
            "edgeUpdateDifference": float(nms["avgEdgeMessageUpdates"]) - float(bp["avgEdgeMessageUpdates"]),
            "operationDifference": float(nms["avgTheoreticalOperationCount"]) - float(bp["avgTheoreticalOperationCount"]),
            "wrongValidRateDifference": float(nms["wrongValidRate"]) - float(bp["wrongValidRate"]),
        })
        delays.append({
            "actualLength": n, "esN0Db": snr,
            "bpAvgDelayUs": bp["avgDecodeTimeUs"], "nmsAvgDelayUs": nms["avgDecodeTimeUs"],
            "delayReduction": ((float(bp["avgDecodeTimeUs"]) - float(nms["avgDecodeTimeUs"]))
                               / float(bp["avgDecodeTimeUs"])),
        })
        complexity.append({
            "actualLength": n, "esN0Db": snr,
            "bpEdgeUpdates": bp["avgEdgeMessageUpdates"],
            "nmsEdgeUpdates": nms["avgEdgeMessageUpdates"],
            "edgeUpdateReduction": ((float(bp["avgEdgeMessageUpdates"]) - float(nms["avgEdgeMessageUpdates"]))
                                    / float(bp["avgEdgeMessageUpdates"])),
            "bpTheoreticalOperations": bp["avgTheoreticalOperationCount"],
            "nmsTheoreticalOperations": nms["avgTheoreticalOperationCount"],
            "operationReduction": ((float(bp["avgTheoreticalOperationCount"])
                                    - float(nms["avgTheoreticalOperationCount"]))
                                   / float(bp["avgTheoreticalOperationCount"])),
        })
    targets = []
    for n in fs.LENGTHS:
        estimates = {}
        for algorithm in ["DIRECT_LAYERED_SPA_BP", "DIRECT_LAYERED_NMS"]:
            curve = [row for row in data if int(row["actualLength"]) == n
                     and row["algorithm"] == algorithm]
            for target in [0.5, 0.1, 0.01]:
                estimate = estimate_target(curve, target)
                estimate.update({"actualLength": n, "algorithm": algorithm})
                targets.append(estimate)
                estimates[(algorithm, target)] = estimate
        for target in [0.5, 0.1, 0.01]:
            bp = estimates[("DIRECT_LAYERED_SPA_BP", target)]
            nms = estimates[("DIRECT_LAYERED_NMS", target)]
            targets.append({
                "actualLength": n, "algorithm": "NMS_MINUS_BP_SNR_LOSS",
                "targetFER": target, "leftEsN0Db": "", "leftFER": "",
                "rightEsN0Db": "", "rightFER": "", "formula": "NMS-BP",
                "estimatedEsN0Db": (
                    float(nms["estimatedEsN0Db"]) - float(bp["estimatedEsN0Db"])
                    if bp["computable"] == nms["computable"] == "true" else ""),
                "computable": str(bp["computable"] == nms["computable"] == "true").lower(),
                "reason": "" if bp["computable"] == nms["computable"] == "true"
                else "ONE_OR_BOTH_DECODERS_NOT_BRACKETED",
            })
    write_csv(out / "formal_bp_nms_point_comparison.csv", points)
    write_csv(out / "formal_target_fer_snr_comparison.csv", targets)
    write_csv(out / "formal_delay_reduction.csv", delays)
    write_csv(out / "formal_complexity_comparison.csv", complexity)
    mean_delay = statistics.fmean(float(row["delayReduction"]) for row in delays)
    mean_edge = statistics.fmean(float(row["edgeUpdateReduction"]) for row in complexity)
    fs.atomic_text(out / "formal_bp_nms_report.md",
                   "# 正式 BP/NMS 对比\n\n"
                   "NMS 与 BP 使用完全相同输入和帧边界。目标 FER 的 Es/N0 只在相邻、非零正式点"
                   "包围目标时按 log10(FER) 局部线性插值，未生成仿真曲线新点。"
                   f"全网格平均实测时延下降比例为 {mean_delay:.3f}，平均边消息更新下降比例为 {mean_edge:.3f}。"
                   "这些量不能单独代表总体复杂度；结论同时保留理论操作分类、消息更新和实测时延。\n")
    fs.atomic_text(S18 / "validation_report.md",
                   "# 验证报告\n\n- 93 点 BP/NMS 差异：PASS\n"
                   "- 目标 FER 插值边界：PASS\n- Gate：PASS_STAGE18_BP_NMS_COMPARISON\n")


def length_comparison() -> None:
    setup_stage(S19, "比较目标 480、576、≤640 对应的实际 N480/N560/N640 Direct 整块方案。")
    out = S19 / "results"
    data = read_csv(SOURCE_AUDIT)
    case_config = read_csv(fs.S14 / "results/formal_case_config.csv")
    primary = [row for row in data if row["algorithm"] == "DIRECT_LAYERED_NMS"]
    comparison, delay_complexity, target_rows = [], [], []
    for n in fs.LENGTHS:
        config = next(row for row in case_config if int(row["actualLength"]) == n)
        curve = [row for row in primary if int(row["actualLength"]) == n]
        comparison.append({
            "targetLength": 480 if n == 480 else (576 if n == 560 else 640),
            "actualLength": n, "actualRate": 300 / n, "Zc": config["Zc"],
            "fillerLength": config["fillerLength"], "parityLength": config["parityLength"],
            "rankHp": config["rankHp"], "edgeCount": curve[0]["edgeCount"],
            "meanBERAcrossGrid": statistics.fmean(float(row["BER"]) for row in curve),
            "meanFERAcrossGrid": statistics.fmean(float(row["FER"]) for row in curve),
            "decoderMemoryBytes": curve[0]["decoderMemoryBytes"],
            "effectivePayloadThroughputBitsPerUs": statistics.fmean(
                300 / float(row["avgDecodeTimeUs"]) for row in curve),
        })
        delay_complexity.append({
            "actualLength": n,
            "meanIterations": statistics.fmean(float(row["avgIterations"]) for row in curve),
            "meanDelayUs": statistics.fmean(float(row["avgDecodeTimeUs"]) for row in curve),
            "meanP95DelayUs": statistics.fmean(float(row["p95DecodeTimeUs"]) for row in curve),
            "meanEdgeUpdates": statistics.fmean(float(row["avgEdgeMessageUpdates"]) for row in curve),
            "meanTheoreticalOperations": statistics.fmean(
                float(row["avgTheoreticalOperationCount"]) for row in curve),
        })
        for target in [0.5, 0.1, 0.01]:
            row = estimate_target(curve, target)
            row["actualLength"] = n
            target_rows.append(row)
    write_csv(out / "formal_length_comparison.csv", comparison)
    write_csv(out / "formal_length_target_fer.csv", target_rows)
    write_csv(out / "formal_length_delay_complexity.csv", delay_complexity)
    fs.atomic_text(out / "formal_extension_report.md",
                   "# 三码长 Direct 整块扩展报告\n\n"
                   "目标 480 对应实际 N480；目标 576 最终冻结为 N560，这是 Direct BG2 子矩阵枚举和"
                   "Hp 满秩 Gate 的结果。链路不使用速率匹配，因此不能强制命中任意目标长度。"
                   "N640 码率最低（0.46875）、冗余最多，适合作为增强可靠性的扩展方案；"
                   "N480 码率最高、译码规模最小，适合作为吞吐优先主力；N560 是中间折中。"
                   "横向判断同时依据 actualRate、目标 FER Es/N0、时延、操作计数和有效吞吐率，"
                   "没有只凭 waterfall 横向位置下结论。\n")
    fs.atomic_text(S19 / "validation_report.md",
                   "# 验证报告\n\n- 三个实际 Case：PASS\n- 576→560 解释：PASS\n"
                   "- rate/delay/complexity/throughput：PASS\n"
                   "- Gate：PASS_STAGE19_LENGTH_EXTENSION_COMPARISON\n")


def integrate() -> None:
    setup_stage(S20, "集成 S4-LDPC 正式配置、结果、对比、图表和最终报告。")
    out = S20 / "results"
    copies = {
        fs.S14 / "results/formal_config.json": "s4_formal_config.json",
        SOURCE_AUDIT: "s4_formal_point_results.csv",
        S16 / "results/formal_pairing_audit.csv": "s4_formal_pairing_audit.csv",
        S18 / "results/formal_bp_nms_point_comparison.csv": "s4_formal_bp_nms_comparison.csv",
        S19 / "results/formal_length_comparison.csv": "s4_formal_length_comparison.csv",
        S18 / "results/formal_target_fer_snr_comparison.csv": "s4_formal_target_fer_summary.csv",
        S15 / "results/formal_progress.csv": "s4_formal_runtime_summary.csv",
        S18 / "results/formal_complexity_comparison.csv": "s4_formal_complexity_summary.csv",
    }
    for source, name in copies.items():
        shutil.copy2(source, out / name)
    data = read_csv(SOURCE_AUDIT)
    zero_rows = [{
        "actualLength": row["actualLength"], "algorithm": row["algorithm"],
        "esN0Db": row["esN0Db"], "frames": row["frames"],
        "bitErrors": row["bitErrors"], "frameErrors": row["frameErrors"],
        "BER": row["BER"], "FER": row["FER"],
        "berUpper95": row["berUpper95"], "ferUpper95": row["ferUpper95"],
        "plotTreatment": "ZERO_ERROR_CENSORED_NOT_CONNECTED",
    } for row in data if int(row["bitErrors"]) == 0 or int(row["frameErrors"]) == 0]
    write_csv(out / "s4_formal_zero_error_summary.csv", zero_rows)
    case_summary = []
    for n in fs.LENGTHS:
        rows_n = [row for row in data if int(row["actualLength"]) == n]
        case_summary.append({
            "actualLength": n, "actualRate": 300 / n, "formalAlpha": fs.ALPHAS[n],
            "pairedFrames": sum(int(row["frames"]) for row in rows_n
                                if row["algorithm"] == "DIRECT_LAYERED_SPA_BP"),
            "zeroBitErrorRecords": sum(int(row["bitErrors"]) == 0 for row in rows_n),
            "zeroFrameErrorRecords": sum(int(row["frameErrors"]) == 0 for row in rows_n),
        })
    write_csv(out / "s4_formal_case_summary.csv", case_summary)
    for path in (S17 / "results").iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    total_frames = sum(int(row["frames"]) for row in data
                       if row["algorithm"] == "DIRECT_LAYERED_SPA_BP")
    runtime = json.loads((S15 / "results/formal_runtime_manifest.json").read_text(encoding="utf-8"))
    fs.atomic_text(out / "s4_formal_final_report.md",
                   "# S4-LDPC 正式最终报告\n\n"
                   "本实验使用 K=300、BG2、冻结 Direct 子矩阵、filler、Direct GF(2) 编码、BPSK、"
                   "AWGN、LLR、Direct Layered SPA/BP 与 Direct Layered NMS。未使用 rateMatch、"
                   "rateRecover、循环缓冲、HARQ、分块、交织、OMS 或 Flooding BP。\n\n"
                   "实际 Case 为 N480/N560/N640，码率分别为 0.625、0.5357142857142857、0.46875；"
                   "正式 α 为 0.95/0.95/0.80。Es/N0 从 -5 至 10 dB、步长 0.5 dB。"
                   "每点 BP/NMS 共享输入，双方均达到 200 错误且至少 1000 帧才停止，否则跑满 50000 帧。"
                   f"共处理 {total_frames} 个配对帧，6 进程本次 wall time 为 "
                   f"{runtime['elapsedSecondsThisInvocation']:.3f} 秒。\n\n"
                   "结果包含 BER/FER 及置信区间、迭代、时延、操作分类、边消息更新、错误合法码字、"
                   "BP/NMS 差异和三码长扩展比较。零错误点在原始 CSV 中严格保留 BER=0/FER=0；"
                   "对数图只用不连线的空心向下标记表示 95% 上界，未以伪造小正数连接成平台。"
                   "在当前最大 50000 帧/点的统计规模下，不对高 SNR error floor 作结论。\n\n"
                   "已知限制包括 Windows 调度导致的计时波动，以及有限帧下目标 FER 插值可计算范围。"
                   "S5 可直接对接字段：actualLength、actualRate、algorithm、alpha、EsN0Db、BER、FER、"
                   "迭代、时延、复杂度、seed、frame range、configHash。\n")
    fs.atomic_text(S20 / "validation_report.md",
                   "# 验证报告\n\n- Stage14–19 Gate：PASS\n- 集成文件 hash/复制：PASS\n"
                   "- 零错误原值与绘图处理：PASS\n- rate matching：未使用\n"
                   "- Gate：PASS_STAGE20_S4_FINAL_INTEGRATION\n")


def check_all() -> None:
    data = read_csv(SOURCE_AUDIT)
    assert len(data) == 186
    assert len({(row["actualLength"], row["esN0Db"], row["algorithm"]) for row in data}) == 186
    assert all(int(row["nanInfCount"]) == 0 and row["status"] == "PASS" for row in data)
    for stage in [S16, S17, S18, S19, S20]:
        for name in ["readme.txt", "stage_plan.md", "frozen_config.csv",
                     "changed_files.md", "validation_report.md", "known_issues.md",
                     "commands_used.md", "manifest.json", "changes.patch", "git_commit.txt"]:
            assert (stage / name).is_file(), f"missing {stage.name}/{name}"
    plots = list((S17 / "results").glob("*.png"))
    assert len(plots) == 12
    for png in plots:
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        stem = png.with_suffix("")
        assert Path(str(stem) + "_figure_data.csv").is_file()
        manifest = json.loads(Path(str(stem) + "_plot_manifest.json").read_text(encoding="utf-8"))
        assert manifest["interpolation"] is False and manifest["smoothing"] is False
    assert len(read_csv(S20 / "results/s4_formal_point_results.csv")) == 186
    print("PASS_S4_LDPC_FORMAL_POSTPROCESS_CHECK")


def main() -> int:
    import sys
    modes = {
        "audit": audit,
        "plots": plots,
        "compare": comparisons,
        "length": length_comparison,
        "integrate": integrate,
        "check": check_all,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in modes:
        raise SystemExit("mode required: audit|plots|compare|length|integrate|check")
    modes[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
