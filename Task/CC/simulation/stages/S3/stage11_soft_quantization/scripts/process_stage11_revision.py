#!/usr/bin/env python3
"""Merge, validate, interpolate, plot and recommend Stage11 quantization."""

from __future__ import annotations

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
from matplotlib import font_manager


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
COARSE_RUNTIME = STAGE / "runtime" / "revision_20260729_coarse"
DENSE_RUNTIME = STAGE / "runtime" / "revision_20260729_dense"
MODES = ["Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Float"]
RATES = ["R12", "R23", "R34"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_units(directory: Path, count: int, rows_per_unit: int) -> list[dict[str, str]]:
    files = sorted(directory.glob("unit_*.csv"))
    if len(files) != count:
        raise RuntimeError(f"{directory}: expected {count} units, got {len(files)}")
    rows = []
    for path in files:
        part = read_csv(path)
        if len(part) != rows_per_unit:
            raise RuntimeError(f"{path.name}: row count mismatch")
        rows.extend(part)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure_font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def validate(rows: list[dict[str, str]], dense: bool) -> None:
    expected_modes = {"Float", "Q5", "Q6", "Q7", "Q8"} if dense else set(MODES)
    expected_snr = {}
    for rate in RATES:
        if not dense:
            expected_snr[rate] = {round(-5 + 0.5 * index, 1) for index in range(31)}
        else:
            low, high = {
                "R12": (-2.0, 0.0),
                "R23": (-0.5, 2.0),
                "R34": (0.5, 3.0),
            }[rate]
            expected_snr[rate] = {
                round(low + 0.1 * index, 1)
                for index in range(round((high - low) / 0.1) + 1)
            }
    coverage: dict[tuple[str, str], set[float]] = defaultdict(set)
    for row in rows:
        coverage[(row["rateCase"], row["quantMode"])].add(
            round(float(row["snrDb"]), 1)
        )
        snr = float(row["snrDb"])
        rate = float(row["actualRate"])
        if not math.isclose(float(row["esN0Db"]), snr, abs_tol=1e-12):
            raise RuntimeError("Es/N0 mismatch")
        if not math.isclose(
            float(row["ebN0Db"]),
            snr - 10 * math.log10(rate),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("Eb/N0 mismatch")
        if not math.isclose(
            float(row["sigmaSquared"]),
            1 / (2 * 10 ** (snr / 10)),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("sigma variance mismatch")
        if int(row["integerOverflowCount"]) != 0 or int(
            row["pathMetricSaturationCount"]
        ) != 0:
            raise RuntimeError("integer overflow/path metric saturation")
    for rate in RATES:
        for mode in expected_modes:
            if coverage[(rate, mode)] != expected_snr[rate]:
                raise RuntimeError(f"coverage mismatch {rate}/{mode}")


def interpolate(points: list[dict[str, str]], target: float) -> dict[str, object]:
    ordered = sorted(points, key=lambda row: float(row["snrDb"]))
    for left, right in zip(ordered, ordered[1:]):
        left_fer, right_fer = float(left["FER"]), float(right["FER"])
        if left_fer >= target >= right_fer and left_fer > 0 and right_fer > 0:
            x0, x1 = float(left["snrDb"]), float(right["snrDb"])
            y0, y1 = math.log10(left_fer), math.log10(right_fer)
            value = x0 + (math.log10(target) - y0) * (x1 - x0) / (y1 - y0)
            return {
                "targetFer": target,
                "leftSnr": x0,
                "leftFer": left_fer,
                "rightSnr": x1,
                "rightFer": right_fer,
                "interpolatedSnr": value,
                "interpolationMethod": "linear_in_log10_FER",
                "coveredByData": "YES",
            }
    return {
        "targetFer": target,
        "leftSnr": "",
        "leftFer": "",
        "rightSnr": "",
        "rightFer": "",
        "interpolatedSnr": "",
        "interpolationMethod": "N/A",
        "coveredByData": "NO",
    }


def snr_losses(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    output = []
    for rate in RATES:
        for target in (0.1, 0.01):
            by_mode = {}
            for mode in MODES:
                by_mode[mode] = interpolate(
                    [
                        row
                        for row in rows
                        if row["rateCase"] == rate and row["quantMode"] == mode
                    ],
                    target,
                )
            float_value = by_mode["Float"]["interpolatedSnr"]
            for mode in MODES:
                item = {
                    "rateCase": rate,
                    "quantMode": mode,
                    **by_mode[mode],
                }
                item["snrLossVsFloat"] = (
                    float(item["interpolatedSnr"]) - float(float_value)
                    if item["coveredByData"] == "YES" and float_value != ""
                    else "N/A"
                )
                output.append(item)
    return output


def line_plot(
    rows: list[dict[str, str]],
    rate: str,
    metric: str,
    filename: str,
) -> dict[str, str]:
    data = [row for row in rows if row["rateCase"] == rate]
    data_path = RESULTS / filename.replace(".png", "_figure_data.csv")
    write_csv(data_path, data)
    figure, axis = plt.subplots(figsize=(9, 6), dpi=150)
    for mode in MODES:
        points = sorted(
            (row for row in data if row["quantMode"] == mode),
            key=lambda row: float(row["snrDb"]),
        )
        y = []
        for row in points:
            value = float(row[metric])
            if value == 0:
                value = float(
                    row["berCiHigh" if metric == "BER" else "ferCiHigh"]
                )
            y.append(value)
        line = axis.plot(
            [float(row["snrDb"]) for row in points],
            y,
            marker="o",
            markersize=2.5,
            linewidth=1,
            label=mode,
        )[0]
        zero = [
            (float(row["snrDb"]), y[index])
            for index, row in enumerate(points)
            if float(row[metric]) == 0
        ]
        if zero:
            axis.scatter(
                [item[0] for item in zero],
                [item[1] for item in zero],
                facecolors="none",
                edgecolors=line.get_color(),
                s=30,
            )
    axis.set_yscale("log")
    axis.set(
        title=f"{rate} 软信息量化 {metric}",
        xlabel="SNR = Es/N0 (dB)",
        ylabel=metric,
    )
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    figure.tight_layout()
    output = RESULTS / filename
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": filename,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def category_plot(
    rows: list[dict[str, str]], rate: str, snr: float
) -> dict[str, str]:
    data = [
        row
        for row in rows
        if row["rateCase"] == rate and math.isclose(float(row["snrDb"]), snr)
    ]
    filename = f"stage11_{rate.lower()}_representative_fer.png"
    data_path = RESULTS / filename.replace(".png", "_figure_data.csv")
    write_csv(data_path, data)
    lookup = {row["quantMode"]: float(row["FER"]) for row in data}
    figure, axis = plt.subplots(figsize=(8, 5), dpi=150)
    axis.bar(MODES, [max(lookup[mode], 1e-8) for mode in MODES])
    axis.set_yscale("log")
    axis.set(
        title=f"{rate} 代表 SNR={snr:g} dB 的 FER",
        xlabel="量化模式",
        ylabel="FER",
    )
    axis.grid(True, axis="y", which="both", alpha=0.25)
    figure.tight_layout()
    output = RESULTS / filename
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": filename,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def grouped_plot(
    rows: list[dict[str, str]],
    metric: str,
    filename: str,
    ylabel: str,
) -> dict[str, str]:
    chosen = []
    representative = {"R12": -0.5, "R23": 1.0, "R34": 2.0}
    for rate, snr in representative.items():
        chosen.extend(
            row
            for row in rows
            if row["rateCase"] == rate and math.isclose(float(row["snrDb"]), snr)
        )
    data_path = RESULTS / filename.replace(".png", "_figure_data.csv")
    write_csv(data_path, chosen)
    width = 0.25
    x = list(range(len(MODES)))
    figure, axis = plt.subplots(figsize=(10, 5.5), dpi=150)
    for rate_index, rate in enumerate(RATES):
        lookup = {
            row["quantMode"]: float(row[metric])
            for row in chosen
            if row["rateCase"] == rate
        }
        axis.bar(
            [value + (rate_index - 1) * width for value in x],
            [lookup[mode] for mode in MODES],
            width,
            label=rate,
        )
    axis.set_xticks(x, MODES)
    axis.set(xlabel="量化模式", ylabel=ylabel)
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    output = RESULTS / filename
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": filename,
        "figureData": data_path.name,
        "figureDataSha256": sha(data_path),
        "outputSha256": sha(output),
    }


def loss_plot(losses: list[dict[str, object]]) -> dict[str, str]:
    data = [
        row
        for row in losses
        if row["quantMode"] != "Float" and row["snrLossVsFloat"] != "N/A"
    ]
    path = RESULTS / "stage11_quantization_snr_loss_figure_data.csv"
    write_csv(path, data)
    figure, axis = plt.subplots(figsize=(9, 5.5), dpi=150)
    for rate in RATES:
        for target in (0.1, 0.01):
            points = [
                row
                for row in data
                if row["rateCase"] == rate and row["targetFer"] == target
            ]
            lookup = {row["quantMode"]: float(row["snrLossVsFloat"]) for row in points}
            axis.plot(
                MODES[:-1],
                [lookup.get(mode, math.nan) for mode in MODES[:-1]],
                marker="o",
                label=f"{rate}, FER={target:g}",
            )
    axis.set(
        title="量化位宽相对 Float 的 SNR 损失",
        xlabel="量化模式",
        ylabel="SNR 损失 (dB)",
    )
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8, ncol=2)
    figure.tight_layout()
    output = RESULTS / "stage11_quantization_snr_loss.png"
    figure.savefig(output)
    plt.close(figure)
    return {
        "name": output.name,
        "figureData": path.name,
        "figureDataSha256": sha(path),
        "outputSha256": sha(output),
    }


def recommendations(rows: list[dict[str, str]], losses: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates = []
    for mode in MODES[:-1]:
        loss_values = [
            float(row["snrLossVsFloat"])
            for row in losses
            if row["quantMode"] == mode and row["snrLossVsFloat"] != "N/A"
        ]
        samples = [row for row in rows if row["quantMode"] == mode]
        candidates.append(
            {
                "quantMode": mode,
                "quantBits": int(mode[1:]),
                "worstSnrLossDb": max(loss_values) if loss_values else math.inf,
                "meanDecodeTimeUs": sum(float(row["avgDecodeTimeUs"]) for row in samples)
                / len(samples),
                "maxTotalMemoryBytes": max(int(row["totalDecoderMemoryBytes"]) for row in samples),
            }
        )
    performance = min(candidates, key=lambda row: row["worstSnrLossDb"])
    qualified = [row for row in candidates if row["worstSnrLossDb"] <= 0.2] or candidates
    balanced = min(
        qualified,
        key=lambda row: (
            row["worstSnrLossDb"]
            + 0.15 * row["maxTotalMemoryBytes"] / max(item["maxTotalMemoryBytes"] for item in qualified)
            + 0.10 * row["meanDecodeTimeUs"] / max(item["meanDecodeTimeUs"] for item in qualified)
        ),
    )
    memory = min(qualified, key=lambda row: row["maxTotalMemoryBytes"])
    latency = min(qualified, key=lambda row: row["meanDecodeTimeUs"])
    chosen = {
        "performanceFirst": performance["quantMode"],
        "balanced": balanced["quantMode"],
        "memoryFirst": memory["quantMode"],
        "latencyFirst": latency["quantMode"],
    }
    for row in candidates:
        row.update(chosen)
    return candidates


def main() -> int:
    configure_font()
    mode = sys.argv[1] if len(sys.argv) > 1 else "final"
    coarse = read_units(COARSE_RUNTIME, 93, 7)
    validate(coarse, False)
    write_csv(RESULTS / "stage11_quantization_coarse_results.csv", coarse)
    if mode == "coarse":
        print(f"PASS_STAGE11_COARSE_MERGE rows={len(coarse)}")
        return 0
    dense = read_units(DENSE_RUNTIME, 73, 5)
    validate(dense, True)
    write_csv(RESULTS / "stage11_quantization_dense_results.csv", dense)
    merged_map = {
        (row["rateCase"], row["quantMode"], round(float(row["snrDb"]), 10)): row
        for row in coarse
    }
    for row in dense:
        merged_map[
            (row["rateCase"], row["quantMode"], round(float(row["snrDb"]), 10))
        ] = row
    merged = sorted(
        merged_map.values(),
        key=lambda row: (
            RATES.index(row["rateCase"]),
            MODES.index(row["quantMode"]),
            float(row["snrDb"]),
        ),
    )
    merged_path = RESULTS / "stage11_soft_quantization_results.csv"
    write_csv(merged_path, merged)
    losses = snr_losses(merged)
    write_csv(RESULTS / "stage11_quantization_snr_loss.csv", losses)
    recommendation = recommendations(merged, losses)
    write_csv(RESULTS / "stage11_quantization_recommendation.csv", recommendation)
    figures = []
    for rate in RATES:
        figures.append(line_plot(merged, rate, "BER", f"stage11_{rate.lower()}_quantization_ber.png"))
        figures.append(line_plot(merged, rate, "FER", f"stage11_{rate.lower()}_quantization_fer.png"))
    figures.extend(
        [
            category_plot(merged, "R12", -0.5),
            category_plot(merged, "R23", 1.0),
            category_plot(merged, "R34", 2.0),
            grouped_plot(merged, "avgDecodeTimeUs", "stage11_quantization_latency.png", "平均译码时间 (μs)"),
            grouped_plot(merged, "totalDecoderMemoryBytes", "stage11_quantization_memory.png", "总译码内存 (byte)"),
            grouped_plot(merged, "trueClipRatePercent", "stage11_quantization_true_clip.png", "trueClipRatePercent (%)"),
            loss_plot(losses),
        ]
    )
    manifest = {
        "stage": "stage11_soft_quantization",
        "inputCsv": merged_path.name,
        "inputSha256": sha(merged_path),
        "coarseRows": len(coarse),
        "denseRows": len(dense),
        "mergedRows": len(merged),
        "figures": figures,
    }
    (RESULTS / "stage11_quantization_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS / "stage11_quantization_plot_check.md").write_text(
        "# Stage11 绘图检查\n\nPASS：按码率拆图；Float 使用分类标签；"
        "所有图来自逐点 CSV；未覆盖 SNR loss 保持 N/A。\n",
        encoding="utf-8",
    )
    print(
        f"PASS_STAGE11_REVISION coarse={len(coarse)} dense={len(dense)} "
        f"balanced={recommendation[0]['balanced']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
