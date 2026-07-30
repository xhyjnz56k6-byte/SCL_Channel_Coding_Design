#!/usr/bin/env python3
"""Process the 2026-07-30 full W/S/D formal Stage13 grid."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
FIGURE_DATA = RESULTS / "figure_data"
RUNTIME = STAGE / "runtime" / "revision_20260730_full_wsd"
RATES = ["R12", "R23", "R34"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_font() -> None:
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def read_units() -> pd.DataFrame:
    frames = []
    for path in sorted(RUNTIME.glob("unit_*.csv")):
        if path.stat().st_size == 0:
            raise RuntimeError(f"empty runtime unit: {path}")
        frames.append(pd.read_csv(path))
    if len(frames) != 8:
        raise RuntimeError(f"expected 8 runtime units, found {len(frames)}")
    data = pd.concat(frames, ignore_index=True)
    data["snrDb"] = data["snrDb"].astype(float).round(1)
    data["windowBits"] = data["windowBits"].astype(int)
    data["slideBits"] = data["slideBits"].astype(int)
    data["dtb"] = data["dtb"].astype(int)
    data["frames"] = data["frames"].astype(int)
    data["bitErrors"] = data["bitErrors"].astype(int)
    data["frameErrors"] = data["frameErrors"].astype(int)
    data["stopReason"] = data["stopReason"].replace(
        {"TARGET_ERRORS_REACHED": "TARGET_FRAME_ERRORS_REACHED"}
    )
    data["normalizedGoodput"] = data["actualRate"] * (1.0 - data["FER"])
    data["runId"] = "stage13_full_wsd_20260730"
    data["configId"] = data["candidateId"]
    return data.sort_values(
        ["experimentId", "rateCase", "candidateId", "snrDb"]
    ).reset_index(drop=True)


def assert_grid(data: pd.DataFrame) -> None:
    expected_snrs = {-5.0 + 0.5 * index for index in range(31)}
    expected = {
        "CONTROL_W": {
            "windowBits": {96, 128, 160, 192},
            "slideBits": {16},
            "dtb": {70},
            "rows": 3 * 4 * 31,
        },
        "CONTROL_S": {
            "windowBits": {160},
            "slideBits": {8, 16, 25, 50},
            "dtb": {70},
            "rows": 3 * 4 * 31,
        },
        "CONTROL_D": {
            "windowBits": {160},
            "slideBits": {16},
            "dtb": {35, 49, 70, 84, 98, 112},
            "rows": 3 * 6 * 31,
        },
    }
    for experiment, spec in expected.items():
        part = data[data["experimentId"] == experiment]
        if len(part) != spec["rows"]:
            raise RuntimeError(f"{experiment} row count {len(part)}")
        if set(part["rateCase"]) != set(RATES):
            raise RuntimeError(f"{experiment} missing rate")
        if set(part["snrDb"]) != expected_snrs:
            raise RuntimeError(f"{experiment} missing SNR")
        for column in ("windowBits", "slideBits", "dtb"):
            if set(part[column]) != spec[column]:
                raise RuntimeError(f"{experiment} bad {column}")
        if (part["frames"] < 1000).any():
            raise RuntimeError(f"{experiment} has frames < minFrames")
        ok_stop = {"TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"}
        if not set(part["stopReason"]).issubset(ok_stop):
            raise RuntimeError(f"{experiment} bad stop reason")
        if part.isna().to_numpy().any():
            raise RuntimeError(f"{experiment} contains NaN")
        if (part["lostBits"] != 0).any() or (part["duplicateBits"] != 0).any():
            raise RuntimeError(f"{experiment} lost/duplicate bit failure")
        if (part["outputLength"] != 300).any():
            raise RuntimeError(f"{experiment} output length failure")
        if (part["finalFlushPass"] != 1).any():
            raise RuntimeError(f"{experiment} final flush failure")
        ber_delta = (
            part["BER"]
            - part["bitErrors"] / (part["frames"] * 300.0)
        ).abs().max()
        fer_delta = (
            part["FER"] - part["frameErrors"] / part["frames"]
        ).abs().max()
        if ber_delta > 1e-15 or fer_delta > 1e-15:
            raise RuntimeError(f"{experiment} BER/FER mismatch")


def write_csv(path: Path, data: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False)


def figure_data(name: str, data: pd.DataFrame) -> Path:
    path = FIGURE_DATA / f"{name}.csv"
    write_csv(path, data)
    return path


def plot_fer_by_rate(data: pd.DataFrame, experiment: str, variable: str) -> list[Path]:
    outputs = []
    part = data[data["experimentId"] == experiment]
    for rate in RATES:
        rate_data = part[part["rateCase"] == rate]
        fig, axis = plt.subplots(figsize=(8.2, 5.2))
        for value, group in rate_data.groupby(variable):
            group = group.sort_values("snrDb")
            valid = group["FER"] > 0.0
            if valid.any():
                axis.semilogy(
                    group.loc[valid, "snrDb"],
                    group.loc[valid, "FER"],
                    marker="o",
                    linewidth=1.6,
                    label=f"{variable}={value}",
                )
            zero = ~valid
            if zero.any():
                axis.scatter(
                    group.loc[zero, "snrDb"],
                    group.loc[zero, "zeroFerUpper95"]
                    if "zeroFerUpper95" in group
                    else [3.0 / n for n in group.loc[zero, "frames"]],
                    marker="o",
                    facecolors="none",
                    edgecolors="black",
                )
        axis.set_title(f"Stage13 {rate} {experiment} FER")
        axis.set_xlabel("SNR = Es/N0 (dB)")
        axis.set_ylabel("FER")
        axis.grid(True, which="both", linestyle="--", alpha=0.35)
        axis.legend()
        fig.tight_layout()
        name = f"stage13_{rate.lower()}_{variable.lower()}_fer_snr"
        png = RESULTS / f"{name}.png"
        fig.savefig(png, dpi=180)
        plt.close(fig)
        figure_data(name, rate_data)
        outputs.append(png)
    return outputs


def summarize_by_candidate(data: pd.DataFrame, experiment: str) -> pd.DataFrame:
    part = data[data["experimentId"] == experiment]
    return (
        part.groupby(["rateCase", "candidateId", "windowBits", "slideBits", "dtb"])
        .agg(
            meanFER=("FER", "mean"),
            meanFirstOutputDelaySymbols=("firstOutputDelaySymbols", "mean"),
            meanAvgDecisionDelaySymbols=("avgDecisionDelaySymbols", "mean"),
            meanP95DecisionDelaySymbols=("p95DecisionDelaySymbols", "mean"),
            maxTotalMemoryBytes=("totalMemoryBytes", "max"),
            meanACSCount=("ACSCount", "mean"),
            meanTracebackOperations=("tracebackOperations", "mean"),
            meanCpuUs=("avgWindowProcessingTimeUs", "mean"),
            frames=("frames", "sum"),
            frameErrors=("frameErrors", "sum"),
        )
        .reset_index()
    )


def plot_summary(summary: pd.DataFrame, name: str, x: str, y: str, ylabel: str) -> Path:
    fig, axis = plt.subplots(figsize=(8.4, 5.0))
    for rate in RATES:
        part = summary[summary["rateCase"] == rate].sort_values(x)
        axis.plot(part[x], part[y], marker="o", linewidth=1.8, label=rate)
    axis.set_title(name.replace("_", " "))
    axis.set_xlabel(x)
    axis.set_ylabel(ylabel)
    axis.grid(True, linestyle="--", alpha=0.35)
    axis.legend()
    fig.tight_layout()
    png = RESULTS / f"{name}.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)
    figure_data(name, summary)
    return png


def write_manifest(paths: list[Path]) -> None:
    manifest = []
    for path in paths:
        manifest.append(
            {
                "file": path.name,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    (RESULTS / "stage13_full_wsd_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_report(data: pd.DataFrame, figures: list[Path]) -> None:
    lines = [
        "# Stage13 全量 W/S/D 控制变量正式实验结果",
        "",
        f"本轮从 `revision_20260730_full_wsd` 的 8 个 shard 合并得到 {len(data)} 行正式数据。",
        "仿真范围为 SNR = Es/N0 -5.0 dB 到 10.0 dB，步长 0.5 dB；每点 minFrames=1000、targetFrameErrors=200、maxFrames=50000。",
        "",
        "## 数据规模",
        "",
    ]
    for experiment in ["CONTROL_W", "CONTROL_S", "CONTROL_D"]:
        part = data[data["experimentId"] == experiment]
        lines.append(
            f"- {experiment}: {len(part)} 点，总帧数 {int(part['frames'].sum())}，"
            f"总误帧 {int(part['frameErrors'].sum())}。"
        )
    lines += ["", "## 结果图", ""]
    for path in figures:
        lines.append(f"![{path.stem}](./{path.name})")
        lines.append("")
    (RESULTS / "stage13_full_wsd_results_analysis.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> int:
    configure_font()
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    data = read_units()
    assert_grid(data)
    all_csv = RESULTS / "stage13_full_wsd_formal_results.csv"
    write_csv(all_csv, data)
    figures: list[Path] = []
    outputs = {
        "CONTROL_W": RESULTS / "stage13_control_w_formal.csv",
        "CONTROL_S": RESULTS / "stage13_control_s_formal.csv",
        "CONTROL_D": RESULTS / "stage13_control_d_formal.csv",
    }
    for experiment, path in outputs.items():
        write_csv(path, data[data["experimentId"] == experiment])
    figures.extend(plot_fer_by_rate(data, "CONTROL_W", "windowBits"))
    figures.extend(plot_fer_by_rate(data, "CONTROL_S", "slideBits"))
    figures.extend(plot_fer_by_rate(data, "CONTROL_D", "dtb"))
    w_summary = summarize_by_candidate(data, "CONTROL_W")
    s_summary = summarize_by_candidate(data, "CONTROL_S")
    d_summary = summarize_by_candidate(data, "CONTROL_D")
    figures.append(
        plot_summary(
            w_summary,
            "stage13_w_first_output_latency",
            "windowBits",
            "meanFirstOutputDelaySymbols",
            "first output delay (symbols)",
        )
    )
    figures.append(
        plot_summary(
            w_summary,
            "stage13_w_avg_p95_latency",
            "windowBits",
            "meanP95DecisionDelaySymbols",
            "P95 decision delay (symbols)",
        )
    )
    figures.append(
        plot_summary(
            w_summary,
            "stage13_w_memory",
            "windowBits",
            "maxTotalMemoryBytes",
            "decoder memory (bytes)",
        )
    )
    figures.append(
        plot_summary(
            w_summary,
            "stage13_w_compute_complexity",
            "windowBits",
            "meanACSCount",
            "ACS count",
        )
    )
    figures.append(
        plot_summary(
            w_summary,
            "stage13_w_cpu_time",
            "windowBits",
            "meanCpuUs",
            "CPU time (us)",
        )
    )
    figures.append(
        plot_summary(
            s_summary,
            "stage13_s_avg_p95_latency",
            "slideBits",
            "meanP95DecisionDelaySymbols",
            "P95 decision delay (symbols)",
        )
    )
    figures.append(
        plot_summary(
            d_summary,
            "stage13_d_traceback_operations",
            "dtb",
            "meanTracebackOperations",
            "traceback operations",
        )
    )
    write_manifest([all_csv, *outputs.values(), *figures])
    write_report(data, figures)
    print(f"PASS_STAGE13_FULL_WSD rows={len(data)} figures={len(figures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
