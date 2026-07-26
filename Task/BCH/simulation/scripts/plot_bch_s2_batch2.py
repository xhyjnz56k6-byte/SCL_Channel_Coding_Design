#!/usr/bin/env python3
"""Create audited PNG-only research figures for BCH S2 batch 2."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


CASE_STYLE = {
    "BCH-S200": ("#1f77b4", "-", "o"),
    "BCH-B200": ("#d62728", "--", "s"),
    "BCH-S300": ("#2ca02c", "-.", "^"),
    "BCH-B300": ("#9467bd", ":", "D"),
    "BCH-B300-426": ("#ff7f0e", "--", "v"),
}
SNR_LABEL = "信噪比 SNR（dB，Bn=Rs）"


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def configure() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 180,
    })


def make_figure(
    repo: Path,
    output_dir: Path,
    filename: str,
    title: str,
    source: Path,
    rows: list[dict[str, str]],
    x: str,
    y: str,
    x_label: str,
    y_label: str,
    y_scale: str,
    profile_field: str | None = None,
) -> dict[str, object]:
    if not rows:
        raise RuntimeError(f"no source rows for {filename}")
    figure_rows: list[dict[str, object]] = []
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        profile = row.get(profile_field, "") if profile_field else ""
        groups.setdefault((row["caseName"], profile), []).append(row)
    fig, ax = plt.subplots(figsize=(16.0, 6.2))
    styles: dict[str, dict[str, str]] = {}
    labels: list[str] = []
    zero_count = 0
    profile_styles = ["-", "--", "-.", ":"]
    for (case, profile), values in sorted(groups.items()):
        color, base_line, marker = CASE_STYLE[case]
        profiles = sorted({key[1] for key in groups if key[0] == case})
        line = (profile_styles[profiles.index(profile) % len(profile_styles)]
                if profile else base_line)
        label = case if not profile else f"{case} / {profile}"
        style_key = f"{case}|{profile or 'DEFAULT'}|{color}|{line}|{marker}"
        if style_key in styles:
            raise RuntimeError("duplicate visual style key")
        styles[style_key] = {"color": color, "lineStyle": line, "marker": marker}
        labels.append(label)
        values = sorted(values, key=lambda row: float(row[x]))
        plotted_x: list[float] = []
        plotted_y: list[float] = []
        for row in values:
            y_value = float(row[y])
            plotted = y_scale != "log" or y_value > 0.0
            if not plotted:
                zero_count += 1
            record: dict[str, object] = dict(row)
            record.update({
                "seriesLabel": label,
                "visualStyleKey": style_key,
                "plotted": str(plotted).lower(),
                "omissionReason": "" if plotted else
                    "ZERO_OBSERVATION_ON_LOG_AXIS",
            })
            figure_rows.append(record)
            if plotted:
                plotted_x.append(float(row[x]))
                plotted_y.append(y_value)
        ax.plot(plotted_x, plotted_y, color=color, linestyle=line, marker=marker,
                markersize=4.5, linewidth=1.4, label=label)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_yscale(y_scale)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7, ncol=2, loc="center left",
              bbox_to_anchor=(1.01, 0.5), borderaxespad=0.0)
    if zero_count and y_scale == "log":
        ax.text(0.01, 0.01, "观测值为0的方案未显示在对数坐标中。",
                transform=ax.transAxes, fontsize=8)
    fig.tight_layout(rect=(0.0, 0.0, 0.62, 1.0))
    png = output_dir / filename
    fig.savefig(png, format="png")
    plt.close(fig)
    if png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("non-PNG output")
    figure_data = output_dir / f"figure_data_{png.stem}.csv"
    write(figure_data, figure_rows)
    return {
        "filename": png.name,
        "title": title,
        "sourceCsv": str(source.relative_to(repo)).replace("\\", "/"),
        "sourceCsvSha256": sha256(source),
        "figureDataCsv": str(figure_data.relative_to(repo)).replace("\\", "/"),
        "figureDataSha256": sha256(figure_data),
        "pngSha256": sha256(png),
        "xColumn": x,
        "xLabel": x_label,
        "xUnit": "dB" if x == "snrDb" else
                 ("degree" if "Rotation" in x else "symbol/bit"),
        "yColumn": y,
        "yLabel": y_label,
        "yUnit": "ratio" if y != "avgTotalReceiverTimeUs" else "us",
        "xTransformFormula": (
            "snrDb=sourcePayloadEbN0Db+10*log10(frameRate)"
            if x == "snrDb" else "IDENTITY"
        ),
        "bandwidthConvention": "Bn_EQUALS_Rs" if x == "snrDb" else "NOT_APPLICABLE",
        "xSemantic": (
            "NORMALIZED_WAVEFORM_SNR_PS_OVER_PN"
            if x == "snrDb" else "DIRECT_PARAMETER"
        ),
        "yScale": y_scale,
        "zeroHandlingPolicy": "OMIT_ZERO_ON_LOG_AXIS_PRESERVE_IN_FIGURE_DATA",
        "seriesStyles": styles,
        "legendLabels": labels,
        "visualStyleKeys": list(styles),
        "sourcePointCount": len(rows),
        "figureDataPointCount": len(figure_rows),
        "omittedZeroCount": zero_count,
        "dpi": 180,
        "matplotlibVersion": matplotlib.__version__,
        "gitCommit": "WORKTREE",
    }


def main() -> int:
    configure()
    repo = Path(__file__).resolve().parents[4]
    stages = repo / "Task/BCH/simulation/stages"
    output = stages / "s2_multi_channel_adaptation" / "figures"
    output.mkdir(parents=True, exist_ok=True)
    specs: list[tuple[str, str, Path, list[dict[str, str]], str, str, str, str, str, str | None]] = []

    cfo_phase_path = stages / "s2_05_residual_cfo/cfo_phase_aggregate_summary.csv"
    cfo_phase = read(cfo_phase_path)
    for target, title, name in [
        ("FER", "残余频偏旋转角与误帧率", "bch_s2_cfo_rotation_fer.png"),
        ("BER", "残余频偏旋转角与误码率", "bch_s2_cfo_rotation_ber.png"),
    ]:
        chosen = []
        for case in CASE_STYLE:
            case_rows = [r for r in cfo_phase if r["caseName"] == case]
            middle = sorted({float(r["sourcePayloadEbN0Db"]) for r in case_rows})[1]
            chosen.extend(r for r in case_rows
                          if float(r["sourcePayloadEbN0Db"]) == middle)
        specs.append((name, title, cfo_phase_path, chosen, "frameRotationDeg",
                      target, "整帧累计相位旋转（°）",
                      "误帧率 FER" if target == "FER" else "误码率 BER",
                      "log", None))

    cfo_snr_path = stages / "s2_05_residual_cfo/cfo_snr_aggregate_summary.csv"
    cfo_snr = read(cfo_snr_path)
    specs.append(("bch_s2_cfo_snr_fer.png", "残余频偏下的误帧率",
                  cfo_snr_path, cfo_snr, "snrDb", "FER", SNR_LABEL,
                  "误帧率 FER", "log", "frameRotationDeg"))

    blockage_path = stages / "s2_06_short_blockage/blockage_position_summary.csv"
    blockage = [r for r in read(blockage_path)
                if r["blockageStartPolicy"] == "UNIFORM_RANDOM"
                and r["attenuationDb"] in {"-12", "-20"}
                and r["completeBlockage"] in {"0", "False", "false"}]
    for target, title, name in [
        ("FER", "短时遮挡长度与误帧率", "bch_s2_blockage_length_fer.png"),
        ("BER", "短时遮挡长度与误码率", "bch_s2_blockage_length_ber.png"),
    ]:
        chosen = []
        for case in CASE_STYLE:
            case_rows = [r for r in blockage if r["caseName"] == case]
            if case_rows:
                low = min(float(r["sourcePayloadEbN0Db"]) for r in case_rows)
                chosen.extend(r for r in case_rows
                              if float(r["sourcePayloadEbN0Db"]) == low)
        specs.append((name, title, blockage_path, chosen, "blockageLength",
                      target, "遮挡长度（符号）",
                      "误帧率 FER" if target == "FER" else "误码率 BER",
                      "log", "attenuationDb"))

    blockage_snr_path = stages / "s2_06_short_blockage/blockage_formal_snr_summary.csv"
    blockage_snr = read(blockage_snr_path)
    for row in blockage_snr:
        row["profile"] = "M" if row["blockageLength"] == "16" else "H"
    specs.append(("bch_s2_blockage_snr_fer.png", "典型遮挡下的误帧率",
                  blockage_snr_path, blockage_snr, "snrDb", "FER", SNR_LABEL,
                  "误帧率 FER", "log", "profile"))

    burst_path = stages / "s2_07_burst_sensitivity/burst_start_sensitivity.csv"
    burst = [r for r in read(burst_path) if r["burstStartPolicy"] == "UNIFORM_RANDOM"]
    for mode, title, name in [
        ("PURE", "纯突发翻转长度敏感性", "bch_s2_pure_burst_fer.png"),
        ("AWGN", "AWGN 与突发翻转联合敏感性", "bch_s2_awgn_burst_fer.png"),
    ]:
        chosen = [r for r in burst if r["burstMode"] == mode]
        if mode == "AWGN":
            reduced: list[dict[str, str]] = []
            for case in CASE_STYLE:
                values = [r for r in chosen if r["caseName"] == case]
                if values:
                    low = min(float(r["sourcePayloadEbN0Db"]) for r in values)
                    reduced.extend(r for r in values
                                   if float(r["sourcePayloadEbN0Db"]) == low)
            chosen = reduced
        specs.append((name, title, burst_path, chosen, "burstLength", "FER",
                      "突发长度（比特）", "误帧率 FER", "log", None))

    comparison_path = stages / "s2_08_channel_adaptation_comparison/channel_adaptation_summary.csv"
    comparison = read(comparison_path)
    selected_channels = {"AWGN", "MULTIPATH_MMSE", "CFO_30_NO_COMPENSATION",
                         "CFO_60_NO_COMPENSATION", "BLOCKAGE_M", "BLOCKAGE_H"}
    comparison = [r for r in comparison if r["channelType"] in selected_channels]
    specs.append(("bch_s2_channel_comparison_fer.png", "多信道适应性综合比较",
                  comparison_path, comparison, "snrDb", "FER", SNR_LABEL,
                  "误帧率 FER", "log", "channelType"))
    specs.append(("bch_s2_channel_comparison_miscorrection.png", "多信道误纠风险",
                  comparison_path, comparison, "snrDb", "miscorrectionRate",
                  SNR_LABEL, "误纠率", "log", "channelType"))
    specs.append(("bch_s2_channel_comparison_failure.png", "多信道译码失败风险",
                  comparison_path, comparison, "snrDb", "decoderFailureRate",
                  SNR_LABEL, "译码失败率", "log", "channelType"))
    specs.append(("bch_s2_channel_receiver_time.png", "多信道接收机平均时延",
                  comparison_path, comparison, "snrDb", "avgTotalReceiverTimeUs",
                  SNR_LABEL, "平均时延（μs）", "linear", "channelType"))

    manifest = [
        make_figure(repo, output, *spec)
        for spec in specs
    ]
    manifest_path = stages / "s2_multi_channel_adaptation/plot_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "schemaVersion": "bch.s2.batch2.plot-manifest.v1",
        "imageFormat": "PNG",
        "nonPngCount": 0,
        "figureCount": len(manifest),
        "figures": manifest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_BCH_S2_BATCH2_PLOT_AUDIT figures={len(manifest)} nonPNG=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
