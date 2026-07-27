#!/usr/bin/env python3
"""Create independently readable corrected BCH S2 research figures."""

from __future__ import annotations

import csv
import hashlib
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE_STYLE = {
    "BCH-S200": ("#1f77b4", "o"),
    "BCH-B200": ("#d62728", "s"),
    "BCH-S300": ("#2ca02c", "^"),
    "BCH-B300": ("#9467bd", "D"),
    "BCH-B300-426": ("#ff7f0e", "v"),
}
SNR_LABEL = "波形信噪比 SNR（dB）"
CHANNEL_LABELS = {
    "AWGN": "AWGN",
    "MULTIPATH_MMSE": "固定多径+MMSE",
    "CFO_30_NO_COMPENSATION_PHI0_ZERO": "残余CFO 30°（φ0=0°）",
    "CFO_60_NO_COMPENSATION_PHI0_ZERO": "残余CFO 60°（φ0=0°）",
    "BLOCKAGE_M": "中度遮挡（-12 dB，16符号）",
    "BLOCKAGE_H": "重度遮挡（-20 dB，32符号）",
}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"empty figure data: {path}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 180,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
    })


class PlotAudit:
    def __init__(self, repo: Path, output: Path) -> None:
        self.repo = repo
        self.output = output
        self.records: list[dict[str, object]] = []
        output.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        fig: plt.Figure,
        filename: str,
        title: str,
        source: Path,
        rows: list[dict[str, object]],
        caption: str,
        x_column: str,
        y_column: str,
        y_scale: str,
    ) -> None:
        fig.tight_layout(rect=(0.0, 0.14, 1.0, 1.0))
        fig.text(
            0.5, 0.018, textwrap.fill(caption, width=105),
            ha="center", va="bottom", fontsize=8.2,
        )
        png = self.output / filename
        fig.savefig(png, format="png", bbox_inches="tight")
        plt.close(fig)
        data = self.output / f"figure_data_{png.stem}.csv"
        write(data, rows)
        self.records.append({
            "filename": filename,
            "title": title,
            "caption": caption,
            "sourceCsv": str(source.relative_to(self.repo)).replace("\\", "/"),
            "sourceCsvSha256": sha256(source),
            "figureDataCsv": str(data.relative_to(self.repo)).replace("\\", "/"),
            "figureDataSha256": sha256(data),
            "pngSha256": sha256(png),
            "figureDataPointCount": len(rows),
            "xColumn": x_column,
            "yColumn": y_column,
            "yScale": y_scale,
            "zeroHandlingPolicy": (
                "PRESERVED_LINEAR_OR_OMITTED_LOG_WITH_EXPLICIT_SET"
            ),
        })


def line_plot(
    audit: PlotAudit,
    filename: str,
    title: str,
    source: Path,
    rows: list[dict[str, str]],
    x: str,
    y: str,
    x_label: str,
    y_label: str,
    caption: str,
    series_key,
    series_label,
    y_scale: str = "log",
    ylim: tuple[float, float] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(series_key(row), []).append(row)
    figure_rows: list[dict[str, object]] = []
    omitted: dict[str, list[str]] = {}
    for index, (key, values) in enumerate(sorted(groups.items())):
        values.sort(key=lambda row: float(row[x]))
        case = values[0]["caseName"]
        color, marker = CASE_STYLE[case]
        line = ["-", "--", "-.", ":"][index % 4]
        px: list[float] = []
        py: list[float] = []
        for row in values:
            value = float(row[y])
            plotted = y_scale != "log" or value > 0.0
            record: dict[str, object] = dict(row)
            record["seriesKey"] = key
            record["plotted"] = str(plotted).lower()
            figure_rows.append(record)
            if plotted:
                px.append(float(row[x]))
                py.append(value)
            else:
                omitted.setdefault(series_label(key, values), []).append(row[x])
        ax.plot(
            px, py, color=color, marker=marker, linestyle=line,
            linewidth=1.5, markersize=4.5, label=series_label(key, values),
        )
    full_caption = caption
    if omitted:
        zero_text = "；".join(
            f"{label}：{','.join(points)}"
            for label, points in omitted.items()
        )
        full_caption += f" 零FER观测（对数轴省略）：{zero_text}。"
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_yscale(y_scale)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7.5, loc="best", framealpha=0.9)
    audit.save(
        fig, filename, title, source, figure_rows, full_caption, x, y, y_scale
    )


def selected_middle_snr(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for case in CASE_STYLE:
        case_rows = [row for row in rows if row["caseName"] == case]
        values = sorted({float(row["sourcePayloadEbN0Db"]) for row in case_rows})
        chosen = values[len(values) // 2]
        output.extend(
            row for row in case_rows
            if float(row["sourcePayloadEbN0Db"]) == chosen
        )
    return output


def make_cfo_plots(
    audit: PlotAudit, cfo_path: Path, phase_path: Path,
) -> None:
    cfo = read(cfo_path)
    chosen = selected_middle_snr(cfo)
    for payload, label in ((200, "200"), (300, "300")):
        rows = [row for row in chosen if int(row["payloadLength"]) == payload]
        line_plot(
            audit,
            f"bch_s2_{label}bit_residual_cfo_fer.png",
            f"{label}比特BCH残余频偏误帧率",
            cfo_path,
            rows,
            "frameRotationDeg",
            "FER",
            "整帧累计相位旋转（°）",
            "误帧率 FER",
            "静态初始相位已同步（φ0=0°），仅残余频偏不补偿；"
            "各曲线图例给出各自AWGN参考工作点。横轴为帧首尾累计旋转，"
            "不同码长下同一角度不代表相同归一化频偏；连线仅引导视线。",
            lambda row: row["caseName"],
            lambda key, values: (
                f"{key}，Eb/N0={float(values[0]['sourcePayloadEbN0Db']):g} dB"
            ),
        )
    phase = [
        row for row in read(phase_path)
        if float(row["frameRotationDeg"]) == 0.0
    ]
    line_plot(
        audit,
        "bch_s2_initial_carrier_phase_sensitivity.png",
        "BCH初始载波相位偏差敏感性",
        phase_path,
        phase,
        "initialPhaseDeg",
        "FER",
        "初始载波相位偏差 φ0（°）",
        "误帧率 FER",
        "固定整帧累计旋转为0°；四个初始相位分别展示、未聚合。"
        "该附加实验不作为残余CFO主结论；纵轴0～1完整展示。",
        lambda row: row["caseName"],
        lambda key, values: (
            f"{key}，Eb/N0={float(values[0]['sourcePayloadEbN0Db']):g} dB"
        ),
        y_scale="linear",
        ylim=(0.0, 1.0),
    )


def make_burst_plots(audit: PlotAudit, burst_path: Path) -> None:
    all_rows = read(burst_path)
    low = [
        row for row in all_rows
        if row["burstStartPolicy"] == "UNIFORM_RANDOM"
        and int(row["burstLength"]) <= 16
    ]
    guarantees = {
        "BCH-S200": 1, "BCH-S300": 1, "BCH-B200": 6,
        "BCH-B300": 10, "BCH-B300-426": 14,
    }
    line_plot(
        audit,
        "bch_s2_pure_burst_low_length_local.png",
        "纯突发错误低长度局部结果",
        burst_path,
        low,
        "burstLength",
        "FER",
        "连续翻转长度（bit）",
        "误帧率 FER",
        "无AWGN；硬判决后连续比特翻转；随机合法起点。"
        "理论保证纠错区已写入图例，零FER按原值在线性坐标展示；"
        "连线仅引导视线。",
        lambda row: row["caseName"],
        lambda key, values: f"{key}（保证≤{guarantees[key]} bit）",
        y_scale="linear",
        ylim=(0.0, 1.0),
    )
    boundary = [
        row for row in all_rows
        if row["caseName"] in {"BCH-S200", "BCH-S300"}
        and int(row["burstLength"]) == 2
    ]
    fig, ax = plt.subplots(figsize=(9.6, 6.2))
    policies = sorted({row["burstStartPolicy"] for row in boundary})
    width = 0.36
    figure_rows: list[dict[str, object]] = []
    for case_index, case in enumerate(("BCH-S200", "BCH-S300")):
        values = []
        for policy in policies:
            row = next(
                item for item in boundary
                if item["caseName"] == case
                and item["burstStartPolicy"] == policy
            )
            values.append(float(row["FER"]))
            figure_rows.append(dict(row))
        color, _ = CASE_STYLE[case]
        positions = [
            index + (case_index - 0.5) * width for index in range(len(policies))
        ]
        ax.bar(positions, values, width=width, color=color, label=case)
    ax.set_xticks(range(len(policies)), policies, rotation=25, ha="right")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("误帧率 FER")
    ax.set_title("S200/S300突发错误起点与子块边界敏感性")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    audit.save(
        fig,
        "bch_s2_segmented_burst_boundary_sensitivity.png",
        "S200/S300突发错误起点与子块边界敏感性",
        burst_path,
        figure_rows,
        "无噪声、连续2 bit翻转。ONE_BEFORE_SEGMENT_BOUNDARY从第14位起，"
        "跨越15-bit子块边界、每块各1错；ON_SEGMENT_BOUNDARY从新子块起，"
        "两错位于同一子块。起点策略为离散类别，不作连续拟合。",
        "burstStartPolicy",
        "FER",
        "linear",
    )


def make_blockage_plots(audit: PlotAudit, blockage_path: Path) -> None:
    all_rows = read(blockage_path)
    selected = [
        row for row in selected_middle_snr(all_rows)
        if row["blockageStartPolicy"] == "UNIFORM_RANDOM"
        and row["completeBlockage"] == "0"
        and int(float(row["attenuationDb"])) in {-12, -20}
    ]
    for payload, label in ((200, "200"), (300, "300")):
        rows = [row for row in selected if int(row["payloadLength"]) == payload]
        line_plot(
            audit,
            f"bch_s2_{label}bit_blockage_length_fer.png",
            f"{label}比特BCH短时遮挡长度与误帧率",
            blockage_path,
            rows,
            "blockageLength",
            "FER",
            "遮挡长度（符号）",
            "误帧率 FER",
            "随机合法遮挡起点；图例明确遮挡衰减及各码参考工作点。"
            "各码使用自身AWGN参考点，不表示统一物理SNR横向排名；"
            "长度64若仍满足目标，只解释为容忍下界≥64；连线仅引导视线。",
            lambda row: f"{row['caseName']}|{row['attenuationDb']}",
            lambda key, values: (
                f"{values[0]['caseName']}，{float(values[0]['attenuationDb']):g} dB，"
                f"Eb/N0={float(values[0]['sourcePayloadEbN0Db']):g} dB"
            ),
        )


def make_comparison_plots(audit: PlotAudit, comparison_path: Path) -> None:
    rows = read(comparison_path)
    for payload, label in ((200, "200"), (300, "300")):
        selected = [row for row in rows if int(row["payloadLength"]) == payload]
        line_plot(
            audit,
            f"bch_s2_{label}bit_channel_comparison_fer.png",
            f"{label}比特BCH分信道误帧率比较",
            comparison_path,
            selected,
            "snrDb",
            "FER",
            SNR_LABEL,
            "误帧率 FER",
            "Bn=Rs，SNR=Eb/N0+10log10(R)。同一图仅用于该输入长度内观察；"
            "CFO固定φ0=0°且不补偿。各信道采样网格和停止条件见数据表。",
            lambda row: f"{row['caseName']}|{row['channelType']}",
            lambda key, values: (
                f"{values[0]['caseName']}，"
                f"{CHANNEL_LABELS.get(values[0]['channelType'], values[0]['channelType'])}"
            ),
        )
    pairs = [
        ("MULTIPATH_MMSE", "bch_s2_awgn_vs_multipath_fer.png", "AWGN与固定多径MMSE误帧率"),
        ("CFO_30_NO_COMPENSATION_PHI0_ZERO", "bch_s2_awgn_vs_cfo30_fer.png", "AWGN与残余CFO 30°误帧率"),
        ("CFO_60_NO_COMPENSATION_PHI0_ZERO", "bch_s2_awgn_vs_cfo60_fer.png", "AWGN与残余CFO 60°误帧率"),
        ("BLOCKAGE_M", "bch_s2_awgn_vs_blockage_m_fer.png", "AWGN与中度遮挡误帧率"),
        ("BLOCKAGE_H", "bch_s2_awgn_vs_blockage_h_fer.png", "AWGN与重度遮挡误帧率"),
    ]
    for channel, filename, title in pairs:
        selected = [
            row for row in rows if row["channelType"] in {"AWGN", channel}
        ]
        line_plot(
            audit, filename, title, comparison_path, selected,
            "snrDb", "FER", SNR_LABEL, "误帧率 FER",
            "Bn=Rs，SNR=Eb/N0+10log10(R)。CFO曲线固定φ0=0°且不补偿；"
            "遮挡为随机合法起点。曲线只在观测区间内解释，不外推。",
            lambda row: f"{row['caseName']}|{row['channelType']}",
            lambda key, values: (
                f"{values[0]['caseName']}，"
                f"{CHANNEL_LABELS.get(values[0]['channelType'], values[0]['channelType'])}"
            ),
        )


def representative_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["caseName"], row["channelType"]), []).append(row)
    output = []
    for values in groups.values():
        values.sort(key=lambda row: float(row["snrDb"]))
        output.append(values[len(values) // 2])
    return output


def make_outcome_plots(audit: PlotAudit, risk_path: Path) -> None:
    rows = representative_rows(read(risk_path))
    for payload, label in ((200, "200"), (300, "300")):
        selected = [
            row for row in rows
            if (("200" in row["caseName"]) == (payload == 200))
        ]
        selected.sort(key=lambda row: (row["caseName"], row["channelType"]))
        names = [
            f"{row['caseName']}\n{CHANNEL_LABELS.get(row['channelType'], row['channelType'])}"
            for row in selected
        ]
        success = [float(row["trueSuccessRate"]) for row in selected]
        misc = [float(row["miscorrectionRate"]) for row in selected]
        failure = [float(row["decoderFailureRate"]) for row in selected]
        fig, ax = plt.subplots(figsize=(11.0, 7.2))
        x = range(len(selected))
        ax.bar(x, success, label="真实成功", color="#2ca02c")
        ax.bar(x, misc, bottom=success, label="误纠", color="#ff7f0e")
        ax.bar(
            x, failure,
            bottom=[a + b for a, b in zip(success, misc)],
            label="显式失败", color="#d62728",
        )
        ax.set_xticks(list(x), names, rotation=55, ha="right", fontsize=7)
        ax.set_ylim(0.0, 1.0)
        ax.set_ylabel("帧比例")
        ax.set_title(f"{label}比特BCH真实成功、误纠与显式失败")
        ax.legend(ncol=3, loc="upper center")
        ax.grid(True, axis="y", alpha=0.25)
        audit.save(
            fig,
            f"bch_s2_{label}bit_receiver_outcome_classification.png",
            f"{label}比特BCH真实成功、误纠与显式失败",
            risk_path,
            [dict(row) for row in selected],
            "每个码/信道取SNR网格中间观测点。三部分之和为1。"
            "S200/S300的syndrome lookup通常不提供显式失败状态，"
            "failure=0不代表真实成功，须与误纠联合解读。",
            "caseName|channelType",
            "trueSuccessRate|miscorrectionRate|decoderFailureRate",
            "linear",
        )


def make_timing_plots(
    audit: PlotAudit,
    timing_source_path: Path,
) -> None:
    all_rows = read(timing_source_path)
    metrics = [
        (
            "decode", "译码时延",
            "p50DecodeTimeUs", "p95DecodeTimeUs",
            "译码器执行时延（μs/帧）",
        ),
        (
            "preprocessing", "信道前处理时延",
            "medianPreprocessingTimeUs", "p95PreprocessingTimeUs",
            "信道前处理时延（μs/帧）",
        ),
        (
            "receiver", "端到端接收机时延",
            "medianReceiverTimeUs", "p95ReceiverTimeUs",
            "端到端接收机时延（μs/帧）",
        ),
    ]
    for payload, label in ((200, "200"), (300, "300")):
        selected = [
            row for row in all_rows
            if int(row["payloadLength"]) == payload
        ]
        selected.sort(key=lambda row: (row["caseName"], row["timingProfile"]))
        names = [
            f"{row['caseName']}\n{row['timingProfile']}" for row in selected
        ]
        for slug, metric_title, median_field, p95_field, y_label in metrics:
            median = [float(row[median_field]) for row in selected]
            p95 = [float(row[p95_field]) for row in selected]
            fig, ax = plt.subplots(figsize=(10.5, 7.4))
            x = list(range(len(selected)))
            ax.plot(x, median, "o-", label="中位数 P50")
            ax.plot(x, p95, "s--", label="P95")
            ax.set_xticks(x, names, rotation=45, ha="right", fontsize=7)
            ax.set_ylabel(y_label)
            ax.set_title(f"{label}比特BCH{metric_title}分位数")
            ax.grid(True, alpha=0.25)
            ax.legend()
            audit.save(
                fig,
                f"bch_s2_{label}bit_{slug}_timing_quantiles.png",
                f"{label}比特BCH{metric_title}分位数",
                timing_source_path,
                [dict(row) for row in selected],
                "profile在计时前只初始化一次；只重跑计时，不替换BER/FER。"
                "AWGN前处理定义为0；CFO前处理含复旋转、复噪声与硬判决；"
                "遮挡前处理含幅度修改、噪声与硬判决。主图显示P50与P95，"
                "均值、P99及最大值保留在数据表。",
                "caseName|timingProfile",
                f"{median_field}|{p95_field}",
                "linear",
            )


def main() -> int:
    configure()
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    cfo_stage = stages / "s2_05_residual_cfo_corrected"
    comparison_stage = stages / "s2_08_channel_adaptation_comparison_corrected"
    result_output = (
        repo / "Task/BCH/simulation/results/s2_batch2_corrected/published/figures"
    )
    stage_output = comparison_stage / "figures"
    audit = PlotAudit(repo, result_output)

    cfo_path = cfo_stage / "cfo_phi0_zero_summary.csv"
    phase_path = cfo_stage / "initial_phase_sensitivity_summary.csv"
    legacy_burst_path = (
        stages / "s2_07_burst_sensitivity/pure_burst_summary.csv"
    )
    corrected_burst_path = (
        comparison_stage / "pure_burst_guaranteed_region_summary.csv"
    )
    merged_burst: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in read(legacy_burst_path) + read(corrected_burst_path):
        merged_burst[(
            row["caseName"], row["burstLength"], row["burstStartPolicy"]
        )] = row
    burst_path = comparison_stage / "pure_burst_low_length_corrected_summary.csv"
    write(burst_path, [dict(row) for row in merged_burst.values()])
    blockage_path = (
        stages / "s2_06_short_blockage/blockage_formal_parameter_summary.csv"
    )
    comparison_path = comparison_stage / "channel_adaptation_summary.csv"
    risk_path = comparison_stage / "miscorrection_risk_summary.csv"
    impairment_timing_path = (
        comparison_stage / "impairment_receiver_timing_audit.csv"
    )
    awgn_timing_path = comparison_stage / "awgn_receiver_timing_audit.csv"
    timing_rows = read(impairment_timing_path)
    for row in timing_rows:
        if row["channelType"] == "RESIDUAL_CFO":
            row["timingProfile"] = (
                f"CFO {int(float(row['frameRotationDeg']))}°"
            )
        else:
            row["timingProfile"] = (
                "中度遮挡（-12 dB，16符号）"
                if int(row["blockageLength"]) == 16
                else "重度遮挡（-20 dB，32符号）"
            )
    for row in read(awgn_timing_path):
        row["timingProfile"] = "AWGN（计时专用复测）"
        row["avgPreprocessingTimeUs"] = "0"
        row["medianPreprocessingTimeUs"] = "0"
        row["p95PreprocessingTimeUs"] = "0"
        row["p99PreprocessingTimeUs"] = "0"
        row["maxPreprocessingTimeUs"] = "0"
        row["avgTotalReceiverTimeUs"] = row["avgDecodeTimeUs"]
        row["medianReceiverTimeUs"] = row["p50DecodeTimeUs"]
        row["p95ReceiverTimeUs"] = row["p95DecodeTimeUs"]
        row["p99ReceiverTimeUs"] = row["p99DecodeTimeUs"]
        row["maxReceiverTimeUs"] = row["maxDecodeTimeUs"]
        timing_rows.append(row)
    timing_source_path = comparison_stage / "receiver_timing_quantile_source.csv"
    write(timing_source_path, [dict(row) for row in timing_rows])

    make_cfo_plots(audit, cfo_path, phase_path)
    make_burst_plots(audit, burst_path)
    make_blockage_plots(audit, blockage_path)
    make_comparison_plots(audit, comparison_path)
    make_outcome_plots(audit, risk_path)
    make_timing_plots(audit, timing_source_path)

    stage_output.mkdir(parents=True, exist_ok=True)
    for path in result_output.iterdir():
        if path.is_file():
            target = stage_output / path.name
            target.write_bytes(path.read_bytes())
    manifest = {
        "schemaVersion": "bch.s2.corrected.plot_manifest.v1",
        "figureCount": len(audit.records),
        "nonPngCount": 0,
        "resultDirectory": str(result_output.relative_to(repo)).replace("\\", "/"),
        "figures": audit.records,
        "gate": "PASS_BCH_S2_CORRECTED_PLOT_AUDIT",
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (comparison_stage / "plot_manifest.json").write_text(text, encoding="utf-8")
    (
        repo / "Task/BCH/simulation/results/s2_batch2_corrected/published/"
        "plot_manifest.json"
    ).write_text(text, encoding="utf-8")
    print(f"PASS_BCH_S2_CORRECTED_PLOT_AUDIT figures={len(audit.records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
