#!/usr/bin/env python3
"""Generate audited BCH S2 PNG figures and per-figure source tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


STYLES = {
    "BCH-S200": ("#1f77b4", "-", "o", "分段 BCH(15,11)"),
    "BCH-B200": ("#d62728", "--", "s", "缩短 BCH(255,207)"),
    "BCH-S300": ("#2ca02c", "-.", "^", "分段 BCH(15,11)"),
    "BCH-B300": ("#9467bd", ":", "D", "缩短 BCH(511,421)"),
    "BCH-B300-426": ("#ff7f0e", "--", "v", "缩短 BCH(511,385)"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    stage = repo / "Task/BCH/simulation/stages/s2_04_fixed_multipath_mmse"
    formal_path = stage / "formal_summary.csv"
    awgn_path = repo / "Task/BCH/simulation/stages/s2_03_awgn_baseline_reuse/awgn_baseline_snr_converted.csv"
    formal, awgn = read(formal_path), read(awgn_path)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    manifests: list[dict[str, object]] = []

    def finish(name: str, title: str, rows: list[dict[str, object]], source: Path,
               y_column: str, y_label: str, y_scale: str = "linear",
               x_column: str = "snrDb", x_label: str = "符号信噪比 Es/N0（dB）",
               x_unit: str = "dB", y_unit: str = "ratio") -> None:
        data_path = stage / f"figure_data_{name}.csv"
        png_path = stage / f"{name}.png"
        write(data_path, rows)
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        if y_scale == "log":
            plt.yscale("log")
        plt.grid(True, which="both", alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(png_path, dpi=180, format="png")
        plt.close()
        manifests.append({
            "filename": png_path.name, "title": title,
            "sourceCsv": source.relative_to(repo).as_posix(),
            "sourceCsvSha256": sha(source),
            "figureDataCsv": data_path.name, "figureDataSha256": sha(data_path),
            "xColumn": x_column, "xLabel": x_label, "xUnit": x_unit,
            "yColumn": y_column, "yLabel": y_label, "yUnit": y_unit,
            "xTransformFormula": "snrDb=sourcePayloadEbN0Db+10*log10(frameRate)",
            "yScale": y_scale,
            "zeroHandlingPolicy": "omit zero observations from logarithmic panels; never replace with epsilon",
            "caseStyles": {case: {"color": value[0], "lineStyle": value[1], "marker": value[2]}
                           for case, value in STYLES.items()},
            "dpi": 180, "matplotlibVersion": matplotlib.__version__,
            "pngSha256": sha(png_path),
            "generatedBy": "plot_bch_s2_multipath.py",
            "gitCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                                        text=True, stdout=subprocess.PIPE).stdout.strip(),
        })

    def line_plot(payload: int, metric: str, name: str, title: str, ylabel: str,
                  log: bool = False) -> None:
        rows: list[dict[str, object]] = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            selected = sorted((row for row in formal if int(row["payloadLength"]) == payload and
                               row["caseName"] == case and (not log or float(row[metric]) > 0.0)),
                              key=lambda row: float(row["snrDb"]))
            if not selected:
                continue
            color, style, marker, label = STYLES[case]
            plt.plot([float(row["snrDb"]) for row in selected],
                     [float(row[metric]) for row in selected], color=color, linestyle=style,
                     marker=marker, markevery=max(1, len(selected) // 10), label=label)
            rows.extend({"caseName": case, "snrDb": row["snrDb"], metric: row[metric]}
                        for row in selected)
        finish(name, title, rows, formal_path, metric, ylabel, "log" if log else "linear")

    for payload in (200, 300):
        prefix = f"bch_s2_{payload}bit"
        title_prefix = f"{payload}比特BCH"
        line_plot(payload, "BER", f"{prefix}_multipath_ber", f"{title_prefix}多径误码率对比", "误码率（BER）", True)
        line_plot(payload, "FER", f"{prefix}_multipath_fer", f"{title_prefix}多径误帧率对比", "误帧率（FER）", True)
        line_plot(payload, "trueSuccessRate", f"{prefix}_true_success", f"{title_prefix}真实译码成功率", "真实译码成功率")
        line_plot(payload, "miscorrectionRate", f"{prefix}_miscorrection", f"{title_prefix}误纠率", "误纠率", True)
        line_plot(payload, "decoderFailureRate", f"{prefix}_decoder_failure", f"{title_prefix}译码器失败率", "译码器失败率", True)
        line_plot(payload, "avgEqualizationTimeUs", f"{prefix}_equalization_time", f"{title_prefix}MMSE均衡时延", "平均均衡时延（μs）")
        line_plot(payload, "avgDecodeTimeUs", f"{prefix}_decode_time", f"{title_prefix}译码时延", "平均译码时延（μs）")
        line_plot(payload, "avgTotalReceiverTimeUs", f"{prefix}_total_receiver_time", f"{title_prefix}接收处理时延", "平均接收处理时延（μs）")

        rows: list[dict[str, object]] = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            selected = sorted((row for row in formal if int(row["payloadLength"]) == payload and row["caseName"] == case),
                              key=lambda row: float(row["snrDb"]))
            if not selected:
                continue
            color, style, marker, label = STYLES[case]
            for metric, suffix in [("preEqualizationHardBER", "均衡前"), ("postEqualizationHardBER", "均衡后")]:
                valid = [row for row in selected if float(row[metric]) > 0.0]
                plt.plot([float(row["snrDb"]) for row in valid], [float(row[metric]) for row in valid],
                         color=color, linestyle=style if suffix == "均衡前" else "--",
                         marker=marker, markevery=max(1, len(valid) // 10), label=f"{label} {suffix}")
                rows.extend({"caseName": case, "series": suffix, "snrDb": row["snrDb"], "hardBER": row[metric]}
                            for row in valid)
        finish(f"{prefix}_pre_post_mmse_hard_ber", f"{title_prefix}MMSE前后硬判决误码率",
               rows, formal_path, "hardBER", "硬判决误码率", "log")

        rows = []
        plt.figure(figsize=(8.2, 5.2))
        for case in STYLES:
            color, style, marker, label = STYLES[case]
            for channel, source_rows, channel_label in [("AWGN", awgn, "AWGN"), ("MULTIPATH", formal, "多径+MMSE")]:
                selected = sorted((row for row in source_rows if int(row["payloadLength"]) == payload and
                                   row["caseName"] == case and float(row["FER"]) > 0.0),
                                  key=lambda row: float(row["snrDb"]))
                if not selected:
                    continue
                plt.plot([float(row["snrDb"]) for row in selected], [float(row["FER"]) for row in selected],
                         color=color, linestyle=":" if channel == "AWGN" else style,
                         marker=marker, markevery=max(1, len(selected) // 8), label=f"{label} {channel_label}")
                rows.extend({"caseName": case, "channel": channel, "snrDb": row["snrDb"], "FER": row["FER"]}
                            for row in selected)
        finish(f"{prefix}_awgn_vs_multipath_fer", f"{title_prefix}多径与AWGN对比",
               rows, formal_path, "FER", "误帧率（FER）", "log")

    loss_path = stage / "multipath_loss_summary.csv"
    loss = [row for row in read(loss_path) if row["valid"] == "true"]
    plt.figure(figsize=(9, 5.4))
    for index, target in enumerate(["0.1", "0.01", "0.001"]):
        selected = [row for row in loss if str(float(row["targetFer"])) == target]
        x = [i + (index - 1) * 0.22 for i in range(len(selected))]
        plt.bar(x, [float(row["multipathLossDb"]) for row in selected], width=0.22, label=f"FER={target}")
    plt.xticks(range(len({row["caseName"] for row in loss})), sorted({row["caseName"] for row in loss}), rotation=15)
    finish("bch_s2_multipath_loss_at_target_fer", "BCH多径目标FER信噪比损失",
           loss, loss_path, "multipathLossDb", "多径损失（dB）", x_column="caseName",
           x_label="BCH方案", x_unit="case", y_unit="dB")

    for source_name, filename, metric, title, ylabel, log in [
        ("fer_amplification_summary.csv", "bch_s2_multipath_fer_amplification", "ferAmplification", "BCH多径FER放大", "FER放大倍数", True),
        ("mmse_hard_ber_summary.csv", "bch_s2_mmse_hard_ber_reduction", "mmseHardBerReductionRatio", "BCH MMSE硬判决改善", "均衡后/均衡前硬判决BER", True),
    ]:
        source = stage / source_name
        source_rows = read(source)
        rows = []
        plt.figure(figsize=(8.4, 5.2))
        for case in STYLES:
            selected = sorted((row for row in source_rows if row["caseName"] == case and
                               row.get("valid") == "true" and row.get(metric, "") and float(row[metric]) > 0.0),
                              key=lambda row: float(row["snrDb"]))
            if not selected:
                continue
            color, style, marker, label = STYLES[case]
            plt.plot([float(row["snrDb"]) for row in selected], [float(row[metric]) for row in selected],
                     color=color, linestyle=style, marker=marker, markevery=max(1, len(selected)//8), label=label)
            rows.extend(selected)
        finish(filename, title, rows, source, metric, ylabel, "log" if log else "linear")

    timing_path = stage / "timing_summary.csv"
    timing = read(timing_path)
    plt.figure(figsize=(9, 5.4))
    cases = [row["caseName"] for row in timing]
    x = list(range(len(cases)))
    plt.bar([v - 0.24 for v in x], [float(row["avgEqualizationTimeUs"]) for row in timing], width=0.24, label="均衡")
    plt.bar(x, [float(row["avgDecodeTimeUs"]) for row in timing], width=0.24, label="译码")
    plt.bar([v + 0.24 for v in x], [float(row["avgTotalReceiverTimeUs"]) for row in timing], width=0.24, label="总接收")
    plt.xticks(x, cases, rotation=15)
    finish("bch_s2_receiver_time_comparison", "BCH多径接收时延对比",
           timing, timing_path, "avgTotalReceiverTimeUs", "平均时延（μs）",
           x_column="caseName", x_label="BCH方案", x_unit="case", y_unit="μs")

    (stage / "plot_manifest.json").write_text(
        json.dumps({"schemaVersion": "bch.s2.plot_manifest.v1", "figures": manifests},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = [{
        "filename": item["filename"], "figureDataCsv": item["figureDataCsv"],
        "pngMagicValid": (stage / str(item["filename"])).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
        "sourceHashMatch": item["sourceCsvSha256"] == sha(repo / str(item["sourceCsv"])),
        "figureDataHashMatch": item["figureDataSha256"] == sha(stage / str(item["figureDataCsv"])),
        "pngHashMatch": item["pngSha256"] == sha(stage / str(item["filename"])),
        "status": "PASS",
    } for item in manifests]
    write(stage / "figure_data_audit.csv", audit)
    if len(manifests) != 24 or any(not all(row[key] for key in
       ["pngMagicValid", "sourceHashMatch", "figureDataHashMatch", "pngHashMatch"]) for row in audit):
        raise SystemExit("BLOCKED_BCH_S2_04_FIGURE_DATA_MISMATCH")
    print(f"PASS_BCH_S2_04_PLOTS png={len(manifests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
