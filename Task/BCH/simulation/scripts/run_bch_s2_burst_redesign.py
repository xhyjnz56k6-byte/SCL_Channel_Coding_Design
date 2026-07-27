#!/usr/bin/env python3
"""S2-07 burst-structure/interleaving experiment driver and publisher."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

CASES = {
    "BCH-S200": ("tab:blue", "o"),
    "BCH-B200": ("tab:red", "s"),
    "BCH-S300": ("tab:green", "^"),
    "BCH-B300": ("tab:purple", "D"),
    "BCH-B300-426": ("tab:orange", "v"),
}
CHANNELS = {
    "AWGN": ("AWGN", "-"),
    "MULTIPATH_MMSE": ("固定多径+MMSE", "--"),
    "CFO_30_NO_COMPENSATION_PHI0_ZERO": ("残余CFO 30°", ":"),
    "CFO_60_NO_COMPENSATION_PHI0_ZERO": ("残余CFO 60°", "-."),
    "BLOCKAGE_M": ("中度遮挡", (0, (5, 1, 1, 1))),
    "BLOCKAGE_H": ("重度遮挡", (0, (3, 1, 1, 1, 1, 1))),
}
CHANNEL_FER_STYLE_MAP = {
    200: {
        ("BCH-S200", "AWGN"): {
            "color": "#0072B2", "linestyle": "-", "marker": "o",
            "markerface": "#0072B2",
        },
        ("BCH-S200", "MULTIPATH_MMSE"): {
            "color": "#D55E00", "linestyle": "--", "marker": "s",
            "markerface": "none",
        },
        ("BCH-S200", "CFO_30_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#009E73", "linestyle": ":", "marker": "^",
            "markerface": "#009E73",
        },
        ("BCH-S200", "CFO_60_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#CC79A7", "linestyle": "-.", "marker": "D",
            "markerface": "none",
        },
        ("BCH-B200", "AWGN"): {
            "color": "#E69F00", "linestyle": (0, (7, 2)), "marker": "v",
            "markerface": "#E69F00",
        },
        ("BCH-B200", "MULTIPATH_MMSE"): {
            "color": "#56B4E9", "linestyle": (0, (3, 1, 1, 1)),
            "marker": "P", "markerface": "none",
        },
        ("BCH-B200", "CFO_30_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#000000", "linestyle": (0, (1, 1)), "marker": "X",
            "markerface": "#000000",
        },
        ("BCH-B200", "CFO_60_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#882255", "linestyle": (0, (5, 1, 1, 1, 1, 1)),
            "marker": "*", "markerface": "none",
        },
    },
    300: {
        ("BCH-S300", "AWGN"): {
            "color": "#0072B2", "linestyle": "-", "marker": "o",
            "markerface": "#0072B2",
        },
        ("BCH-S300", "MULTIPATH_MMSE"): {
            "color": "#D55E00", "linestyle": "--", "marker": "s",
            "markerface": "none",
        },
        ("BCH-S300", "CFO_30_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#009E73", "linestyle": ":", "marker": "^",
            "markerface": "#009E73",
        },
        ("BCH-S300", "CFO_60_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#CC79A7", "linestyle": "-.", "marker": "D",
            "markerface": "none",
        },
        ("BCH-B300", "AWGN"): {
            "color": "#E69F00", "linestyle": (0, (7, 2)), "marker": "v",
            "markerface": "#E69F00",
        },
        ("BCH-B300", "MULTIPATH_MMSE"): {
            "color": "#56B4E9", "linestyle": (0, (3, 1, 1, 1)),
            "marker": "P", "markerface": "none",
        },
        ("BCH-B300", "CFO_30_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#000000", "linestyle": (0, (1, 1)), "marker": "X",
            "markerface": "#000000",
        },
        ("BCH-B300", "CFO_60_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#882255", "linestyle": (0, (5, 1, 1, 1, 1, 1)),
            "marker": "*", "markerface": "none",
        },
        ("BCH-B300-426", "AWGN"): {
            "color": "#44AA99", "linestyle": (0, (9, 2, 1, 2)),
            "marker": "<", "markerface": "#44AA99",
        },
        ("BCH-B300-426", "MULTIPATH_MMSE"): {
            "color": "#AA4499", "linestyle": (0, (2, 1, 2, 3)),
            "marker": ">", "markerface": "none",
        },
        ("BCH-B300-426", "CFO_30_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#999933", "linestyle": (0, (4, 1, 1, 1, 1, 3)),
            "marker": "h", "markerface": "#999933",
        },
        ("BCH-B300-426", "CFO_60_NO_COMPENSATION_PHI0_ZERO"): {
            "color": "#117733", "linestyle": (0, (1, 1, 5, 1)),
            "marker": "p", "markerface": "none",
        },
    },
}

STAGE_DIRS = {
    "s2-07a": "s2_07a_block_burst_correction_boundary",
    "s2-07b": "s2_07b_segmented_boundary_heatmap",
    "s2-07c": "s2_07c_random_burst_performance",
    "s2-07d": "s2_07d_burst_interleaving",
}
GATES = {
    "s2-07a": "PASS_BCH_S2_07A_BLOCK_BURST_CORRECTION_BOUNDARY",
    "s2-07b": "PASS_BCH_S2_07B_SEGMENTED_BOUNDARY_HEATMAP",
    "s2-07c": "PASS_BCH_S2_07C_RANDOM_BURST_PERFORMANCE",
    "s2-07d": "PASS_BCH_S2_07D_BURST_INTERLEAVING",
}


def run(command: list[str], cwd: Path) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"refusing empty CSV: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_matlab() -> str | None:
    candidates = [
        os.environ.get("MATLAB_EXE"),
        shutil.which("matlab"),
        r"D:\Apps\Matlab\bin\matlab.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def matlab_quote(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def validate_matlab_summary(path: Path) -> dict[str, int]:
    rows = read_csv(path)
    if len(rows) != 15:
        raise RuntimeError("MATLAB summary must contain exactly 15 groups")
    mismatch_fields = [
        "encodedMismatch", "burstMismatch", "deinterleaveMismatch",
        "payloadMismatch", "frameMismatch", "statusMismatch",
        "permutationMismatch", "weightMismatch",
    ]
    frames = sum(int(row["Var3"]) for row in rows)
    if frames != 9040:
        raise RuntimeError(f"MATLAB compared {frames} frames, expected 9040")
    for row in rows:
        if row["gate"] != "PASS":
            raise RuntimeError("MATLAB group gate is not PASS")
        for field in mismatch_fields:
            if int(row[field]) != 0:
                raise RuntimeError(f"MATLAB mismatch: {field}")
    return {"groups": len(rows), "frames": frames, "mismatches": 0}


def run_matlab_reference(repo: Path, build: Path, allow_skip: bool) -> bool:
    audit = repo / "Task/BCH/simulation/stages/s2_07_burst_redesign_audit"
    execution = audit / "matlab_execution.json"
    summary = audit / "matlab_reference_summary.csv"
    log_path = audit / "matlab_log.txt"
    matlab = find_matlab()
    if matlab is None:
        record = {
            "schemaVersion": "bch.s2.matlab_execution.v1",
            "executed": False, "skipped": allow_skip,
            "returnCode": None, "gate": "BLOCKED_MATLAB_NOT_AVAILABLE",
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
            "timestampUnix": int(time.time()),
        }
        execution.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        if allow_skip:
            print("BLOCKED_BCH_S2_07_MATLAB_NOT_EXECUTED")
            return False
        raise RuntimeError("MATLAB executable was not found")
    if not (build / "CMakeCache.txt").exists():
        run([
            "cmake", "-G", "MinGW Makefiles",
            "-S", "Task/BCH/simulation/current",
            "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
        ], repo)
    run(["cmake", "--build", str(build), "-j", "4", "--target",
         "export_bch_s2_burst_matlab_vectors"], repo)
    vector_path = repo / (
        "Task/BCH/simulation/results/s2_07_burst_redesign/"
        "matlab/burst_vectors.csv")
    exporter = build / "export_bch_s2_burst_matlab_vectors.exe"
    run([str(exporter), str(vector_path)], repo)
    if summary.exists():
        summary.unlink()
    expression = (
        "addpath('" + matlab_quote(
            repo / "Task/BCH/simulation/matlab_official_validation/matlab")
        + "'); run_bch_s2_burst_redesign_reference('"
        + matlab_quote(vector_path) + "','" + matlab_quote(summary) + "')")
    started = int(time.time())
    completed = subprocess.run(
        [matlab, "-batch", expression], cwd=repo, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log_path.write_text(completed.stdout, encoding="utf-8")
    record = {
        "schemaVersion": "bch.s2.matlab_execution.v1",
        "executed": True, "skipped": False,
        "command": [matlab, "-batch", expression],
        "returnCode": completed.returncode,
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "timestampUnix": started,
        "inputFile": vector_path.relative_to(repo).as_posix(),
        "inputSha256": sha256(vector_path),
        "outputFile": summary.relative_to(repo).as_posix(),
        "logFile": log_path.relative_to(repo).as_posix(),
        "logSha256": sha256(log_path),
    }
    if completed.returncode != 0:
        record["gate"] = "BLOCKED_MATLAB_RETURN_CODE"
        execution.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        raise RuntimeError(
            f"MATLAB failed with return code {completed.returncode}")
    result = validate_matlab_summary(summary)
    record.update(result)
    record["outputSha256"] = sha256(summary)
    record["gate"] = "PASS_BCH_S2_07_MATLAB_BURST_REFERENCE"
    execution.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print("PASS_BCH_S2_07_MATLAB_BURST_REFERENCE "
          f"groups={result['groups']} frames={result['frames']}")
    return True


def configure_chinese() -> None:
    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False


class PlotAudit:
    def __init__(self, root: Path, published: Path) -> None:
        self.root = root
        self.published = published
        self.records: list[dict[str, Any]] = []
        root.mkdir(parents=True, exist_ok=True)
        published.mkdir(parents=True, exist_ok=True)

    def save(
        self, fig: plt.Figure, filename: str, rows: list[dict[str, Any]],
        source: Path, title: str, xlabel: str, ylabel: str,
        xscale: str = "linear", yscale: str = "linear",
        zero_policy: str = "PLOT_ALL_LINEAR",
        visual: list[dict[str, Any]] | None = None,
        interpolation: str = "NONE",
    ) -> None:
        data = self.root / f"figure_data_{Path(filename).stem}.csv"
        image = self.root / filename
        write_csv(data, rows)
        fig.savefig(image, dpi=220, bbox_inches="tight")
        plt.close(fig)
        if image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"not a PNG: {image}")
        shutil.copy2(image, self.published / image.name)
        shutil.copy2(data, self.published / data.name)
        self.records.append({
            "filename": image.name,
            "figureData": data.name,
            "title": title, "xLabel": xlabel, "yLabel": ylabel,
            "xScale": xscale, "yScale": yscale, "zeroPolicy": zero_policy,
            "sourceFile": source.as_posix(),
            "sourceSha256": sha256(source),
            "figureDataSha256": sha256(data),
            "pngSha256": sha256(image),
            "pointCount": len(rows),
            "visualEncoding": visual or [],
            "format": "PNG", "interpolation": interpolation,
        })


def plot_part_a(repo: Path, audit: PlotAudit) -> None:
    source = repo / (
        "Task/BCH/simulation/stages/"
        "s2_08_channel_adaptation_comparison_corrected/"
        "channel_adaptation_summary.csv"
    )
    rows = read_csv(source)
    for row in rows:
        expected = float(row["sourcePayloadEbN0Db"]) + 10.0 * math.log10(
            float(row["frameRate"])
        )
        if abs(float(row["snrDb"]) - expected) > 1e-12:
            raise RuntimeError("Part A SNR transformation audit failed")
        if not math.isfinite(float(row["FER"])):
            raise RuntimeError("Part A nonfinite FER")
    for payload, case_names in (
        (200, {"BCH-S200", "BCH-B200"}),
        (300, {"BCH-S300", "BCH-B300", "BCH-B300-426"}),
    ):
        for blocked, slug, title in (
            (False, "channel", f"{payload}比特BCH信道误帧率比较"),
            (True, "blockage", f"{payload}比特BCH遮挡误帧率比较"),
        ):
            selected = [
                row for row in rows
                if row["caseName"] in case_names
                and row["channelType"].startswith("BLOCKAGE_") == blocked
            ]
            fig, ax = plt.subplots(figsize=(10.0, 6.4))
            figure_rows: list[dict[str, Any]] = []
            visual: list[dict[str, Any]] = []
            triples: set[tuple[str, str, str, str]] = set()
            for case in [name for name in CASES if name in case_names]:
                for channel in CHANNELS:
                    values = [
                        row for row in selected
                        if row["caseName"] == case and row["channelType"] == channel
                    ]
                    if not values:
                        continue
                    values.sort(key=lambda row: float(row["snrDb"]))
                    channel_label, linestyle = CHANNELS[channel]
                    markeredgewidth = 1.2
                    linewidth = 1.5
                    markersize = 5.0
                    if blocked:
                        color, marker = CASES[case]
                        face = "none" if channel == "BLOCKAGE_H" else color
                    else:
                        style = CHANNEL_FER_STYLE_MAP[payload][(case, channel)]
                        color = style["color"]
                        marker = style["marker"]
                        linestyle = style["linestyle"]
                        face = style["markerface"]
                        markeredgewidth = 1.35
                        linewidth = 2.0
                        markersize = 6.6
                    style_key = (color, repr(linestyle), marker, face)
                    if style_key in triples:
                        raise RuntimeError("duplicate visual style tuple")
                    triples.add(style_key)
                    plotted = []
                    for row in values:
                        record: dict[str, Any] = dict(row)
                        record["plotStatus"] = (
                            "PLOTTED" if float(row["FER"]) > 0.0
                            else "OMITTED_ZERO_OBSERVATION"
                        )
                        figure_rows.append(record)
                        if float(row["FER"]) > 0.0:
                            plotted.append(row)
                    if plotted:
                        ax.plot(
                            [float(row["snrDb"]) for row in plotted],
                            [float(row["FER"]) for row in plotted],
                            color=color, marker=marker, markerfacecolor=face,
                            markeredgecolor=color,
                            markeredgewidth=markeredgewidth,
                            linestyle=linestyle, linewidth=linewidth,
                            markersize=markersize,
                            label=f"{case}，{channel_label}",
                        )
                    visual.append({
                        "caseName": case, "channelType": channel,
                        "color": color, "marker": marker,
                        "linestyle": repr(linestyle), "markerface": face,
                        "linewidth": linewidth, "markersize": markersize,
                        "markeredgewidth": markeredgewidth,
                    })
            if not figure_rows or len(visual) > 12:
                raise RuntimeError("Part A split or point coverage failure")
            ax.set_title(title)
            ax.set_xlabel("SNR（dB）")
            ax.set_ylabel("误帧率 FER")
            ax.set_yscale("log")
            ax.grid(True, which="both", alpha=0.25)
            if blocked:
                ax.legend(fontsize=7.5, loc="best")
            else:
                ax.legend(
                    fontsize=7.0, ncol=(2 if payload == 200 else 3),
                    loc="upper center", bbox_to_anchor=(0.5, -0.16),
                    framealpha=0.95, columnspacing=0.9, handlelength=3.0,
                )
                fig.subplots_adjust(bottom=0.28)
            audit.save(
                fig, f"bch_s2_{payload}bit_{slug}_fer_redesigned.png",
                figure_rows, source, title, "SNR（dB）", "误帧率 FER",
                yscale="log", zero_policy="OMITTED_ZERO_OBSERVATION",
                visual=visual,
            )
    print("PASS_BCH_S2_CHANNEL_FER_PLOT_DISTINGUISHABILITY")


def line_plot(
    audit: PlotAudit, source: Path, filename: str, title: str,
    rows: list[dict[str, str]], series_fields: tuple[str, ...],
    xlabel: str = "连续错误长度（bit）", ylabel: str = "误帧率 FER",
    metric: str = "FER",
) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 6.2))
    figure_rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in series_fields), []).append(row)
    visual = []
    for key, values in groups.items():
        values.sort(key=lambda row: int(row["burstLength"]))
        case = values[0]["caseName"]
        color, marker = CASES[case]
        mode = values[0].get("interleaverMode", "NONE")
        linestyle = "--" if mode == "FIXED_RANDOM" else "-"
        ax.plot(
            [int(row["burstLength"]) for row in values],
            [float(row[metric]) for row in values],
            color=color, marker=marker, linestyle=linestyle,
            markersize=4, linewidth=1.4,
            label="，".join(key).replace("NONE", "无交织").replace(
                "FIXED_RANDOM", "固定随机交织"
            ),
        )
        for row in values:
            record: dict[str, Any] = dict(row)
            record["plotStatus"] = "PLOTTED"
            figure_rows.append(record)
        visual.append({
            "series": "|".join(key), "color": color, "marker": marker,
            "linestyle": linestyle,
        })
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0.0, 1.0 if metric == "FER" else None)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    audit.save(fig, filename, figure_rows, source, title, xlabel, ylabel, visual=visual)


def plot_experiments(repo: Path, audit: PlotAudit) -> None:
    stages = repo / "Task/BCH/simulation/stages"
    a_source = stages / STAGE_DIRS["s2-07a"] / "formal_summary.csv"
    a = read_csv(a_source)
    line_plot(
        audit, a_source, "bch_s2_07a_block_burst_boundary.png",
        "整块BCH连续错误纠正边界", a, ("caseName",),
        ylabel="成功起点比例", metric="trueSuccessRate",
    )
    b_source = stages / STAGE_DIRS["s2-07b"] / "boundary_heatmap_summary.csv"
    b = read_csv(b_source)
    for case in ("BCH-S200", "BCH-S300"):
        values = [row for row in b if row["caseName"] == case]
        matrix = np.full((30, 15), np.nan)
        for row in values:
            matrix[int(row["burstLength"]) - 1,
                   int(row["relativeStartInSubblock"])] = float(row["FER"])
        if np.isnan(matrix).any():
            raise RuntimeError("heatmap has missing observations")
        fig, ax = plt.subplots(figsize=(9.6, 7.0))
        image = ax.imshow(
            matrix, origin="lower", aspect="auto", interpolation="nearest",
            cmap="cividis", vmin=0.0, vmax=1.0,
            extent=(-0.5, 14.5, 0.5, 30.5),
        )
        fig.colorbar(image, ax=ax, label="误帧率 FER")
        title = f"{case.replace('BCH-', '')}子块边界突发错误热力图"
        ax.set_title(title)
        ax.set_xlabel("子块内起点位置")
        ax.set_ylabel("连续错误长度（bit）")
        audit.save(
            fig, f"bch_s2_07b_{case.lower().replace('bch-', '')}_heatmap.png",
            [dict(row) for row in values], b_source, title,
            "子块内起点位置", "连续错误长度（bit）",
            zero_policy="PLOT_ALL_LINEAR",
            visual=[{"colormap": "cividis", "vmin": 0, "vmax": 1,
                     "interpolation": "nearest"}],
            interpolation="nearest",
        )
        local_values = [
            row for row in values if int(row["burstLength"]) <= 5
        ]
        local_matrix = np.full((5, 15), np.nan)
        for row in local_values:
            local_matrix[int(row["burstLength"]) - 1,
                         int(row["relativeStartInSubblock"])] = float(row["FER"])
        fig, ax = plt.subplots(figsize=(9.6, 4.4))
        image = ax.imshow(
            local_matrix, origin="lower", aspect="auto",
            interpolation="nearest", cmap="cividis", vmin=0.0, vmax=1.0,
            extent=(-0.5, 14.5, 0.5, 5.5),
        )
        fig.colorbar(image, ax=ax, label="误帧率 FER")
        title = f"{case} 子块边界局部热力图（L=1..5）"
        ax.set_title(title)
        ax.set_xlabel("子块内起点位置 r")
        ax.set_ylabel("连续错误长度 L（bit）")
        audit.save(
            fig, f"bch_s2_07b_{case.lower().replace('bch-', '')}_local_l1_l5.png",
            [dict(row) for row in local_values], b_source, title,
            "子块内起点位置 r", "连续错误长度 L（bit）",
            visual=[{"colormap": "cividis", "vmin": 0, "vmax": 1,
                     "interpolation": "nearest", "region": "L=1..5"}],
            interpolation="nearest",
        )
        guarantee_rows: list[dict[str, Any]] = []
        guarantee_matrix = np.zeros((30, 15))
        for row in values:
            guarantee = 1 if row["theoreticalGuaranteedRegion"] == "true" else 0
            guarantee_matrix[int(row["burstLength"]) - 1,
                             int(row["relativeStartInSubblock"])] = guarantee
            record: dict[str, Any] = dict(row)
            record["guaranteeValue"] = guarantee
            guarantee_rows.append(record)
        fig, ax = plt.subplots(figsize=(9.6, 7.0))
        image = ax.imshow(
            guarantee_matrix, origin="lower", aspect="auto",
            interpolation="nearest",
            cmap=ListedColormap(["#d95f02", "#1b9e77"]), vmin=0, vmax=1,
            extent=(-0.5, 14.5, 0.5, 30.5),
        )
        colorbar = fig.colorbar(image, ax=ax, ticks=[0, 1])
        colorbar.ax.set_yticklabels(["非保证区", "理论保证区"])
        title = f"{case} 理论保证区域（二值图）"
        ax.set_title(title)
        ax.set_xlabel("子块内起点位置 r")
        ax.set_ylabel("连续错误长度 L（bit）")
        audit.save(
            fig, f"bch_s2_07b_{case.lower().replace('bch-', '')}_guarantee_binary.png",
            guarantee_rows, b_source, title,
            "子块内起点位置 r", "连续错误长度 L（bit）",
            visual=[{"colormap": "binary-guarantee", "vmin": 0, "vmax": 1,
                     "interpolation": "nearest"}],
            interpolation="nearest",
        )
    l2_rows = [row for row in b if int(row["burstLength"]) == 2]
    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    l2_visual: list[dict[str, Any]] = []
    for case in ("BCH-S200", "BCH-S300"):
        values = sorted(
            [row for row in l2_rows if row["caseName"] == case],
            key=lambda row: int(row["relativeStartInSubblock"]),
        )
        color, marker = CASES[case]
        ax.plot(
            [int(row["relativeStartInSubblock"]) for row in values],
            [float(row["FER"]) for row in values],
            color=color, marker=marker, linestyle="-", label=case,
        )
        l2_visual.append({
            "series": case, "color": color, "marker": marker,
            "linestyle": "-", "markerface": color,
        })
    ax.axvline(14, color="black", linestyle=":", linewidth=1.2)
    ax.annotate("r=14：跨子块边界", xy=(14, 0), xytext=(9.2, 0.18),
                arrowprops={"arrowstyle": "->"})
    title = "分块 BCH：L=2 时起点位置与 FER"
    ax.set_title(title)
    ax.set_xlabel("子块内起点位置 r")
    ax.set_ylabel("误帧率 FER")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend()
    audit.save(
        fig, "bch_s2_07b_l2_relative_start_fer.png",
        [dict(row, plotStatus="PLOTTED") for row in l2_rows],
        b_source, title, "子块内起点位置 r", "误帧率 FER",
        visual=l2_visual,
    )
    c_source = stages / STAGE_DIRS["s2-07c"] / "formal_summary.csv"
    c = [row for row in read_csv(c_source) if int(row["burstLength"]) <= 32]
    line_plot(
        audit, c_source, "bch_s2_07c_200bit_random_burst_fer.png",
        "200比特BCH随机突发误帧率",
        [row for row in c if int(row["payloadLength"]) == 200], ("caseName",),
    )
    line_plot(
        audit, c_source, "bch_s2_07c_300bit_random_burst_fer.png",
        "300比特BCH随机突发误帧率",
        [row for row in c if int(row["payloadLength"]) == 300], ("caseName",),
    )
    d_source = stages / STAGE_DIRS["s2-07d"] / "formal_summary.csv"
    d = [row for row in read_csv(d_source) if int(row["burstLength"]) <= 32]
    line_plot(
        audit, d_source, "bch_s2_07d_200bit_interleaving_fer.png",
        "200比特BCH交织前后突发误帧率",
        [row for row in d if int(row["payloadLength"]) == 200],
        ("caseName", "interleaverMode"),
    )
    line_plot(
        audit, d_source, "bch_s2_07d_300bit_interleaving_fer.png",
        "300比特BCH交织前后突发误帧率",
        [row for row in d if int(row["payloadLength"]) == 300],
        ("caseName", "interleaverMode"),
    )
    line_plot(
        audit, d_source, "bch_s2_07d_segmented_max_subblock_errors.png",
        "分块BCH交织前后最大子块错误数",
        [row for row in d if row["caseName"] in {"BCH-S200", "BCH-S300"}],
        ("caseName", "interleaverMode"),
        ylabel="解交织后单个子块最大错误数的帧平均值",
        metric="averageMaximumSubblockErrorWeight",
    )
    over_capability: list[dict[str, str]] = []
    for row in d:
        if row["caseName"] not in {"BCH-S200", "BCH-S300"}:
            continue
        record = dict(row)
        record["overCapabilityFrameFraction"] = str(
            1.0 - float(row["fractionAllSubblocksWithinGuaranteedRegion"])
        )
        over_capability.append(record)
    line_plot(
        audit, d_source, "bch_s2_07d_over_capability_frame_fraction.png",
        "交织前后超纠错能力帧比例",
        over_capability, ("caseName", "interleaverMode"),
        ylabel="超出子块保证纠错能力的帧比例",
        metric="overCapabilityFrameFraction",
    )


def audit_stage(repo: Path, stage: str) -> None:
    root = repo / "Task/BCH/simulation/stages" / STAGE_DIRS[stage]
    formal = read_csv(root / "formal_summary.csv")
    smoke = read_csv(root / "smoke_summary.csv")
    if not formal or not smoke:
        raise RuntimeError(f"{stage} empty results")
    for row in formal + smoke:
        numeric = [
            "FER", "BER", "trueSuccessRate", "reportedSuccessRate",
            "decoderFailureRate", "miscorrectionRate",
        ]
        if any(not math.isfinite(float(row[field])) for field in numeric):
            raise RuntimeError(f"{stage} NaN/Inf")
        if int(row["processedFrames"]) <= 0:
            raise RuntimeError(f"{stage} empty point")
    if stage == "s2-07a":
        for row in formal:
            if int(row["burstLength"]) <= int(row["correctionCapabilityT"]):
                if float(row["FER"]) != 0.0 or float(row["miscorrectionRate"]) != 0.0:
                    raise RuntimeError("FAIL_BCH_S2_07A_GUARANTEED_REGION")
    if stage == "s2-07b":
        for row in formal:
            if row["theoreticalGuaranteedRegion"] == "true" and float(row["FER"]) != 0:
                raise RuntimeError("FAIL_BCH_S2_07B_SEGMENT_GUARANTEED_REGION")
        crosses = [
            row for row in formal
            if row["burstLength"] == "2"
            and row["relativeStartInSubblock"] == "14"
        ]
        if len(crosses) != 2 or any(float(row["FER"]) != 0 for row in crosses):
            raise RuntimeError("FAIL_BCH_S2_07B_CROSS_BOUNDARY")
    if stage == "s2-07d":
        if any(row["errorWeightConserved"] != "true" for row in formal):
            raise RuntimeError("FAIL_BCH_S2_07D_ERROR_WEIGHT_CONSERVATION")
        groups: dict[tuple[str, str], set[str]] = {}
        for row in formal:
            groups.setdefault(
                (row["caseName"], row["burstLength"]), set()
            ).add(row["processedFrames"])
        if any(len(values) != 1 for values in groups.values()):
            raise RuntimeError("FAIL_BCH_S2_07D_PAIRED_FRAMES")
    print(GATES[stage])


def derive_stage_files(repo: Path, stage: str) -> None:
    root = repo / "Task/BCH/simulation/stages" / STAGE_DIRS[stage]
    formal = read_csv(root / "formal_summary.csv")
    smoke = read_csv(root / "smoke_summary.csv")
    write_csv(root / "test_summary.csv", [{
        "test": f"{stage}_smoke", "status": "PASS", "rows": len(smoke)
    }, {
        "test": f"{stage}_formal", "status": "PASS", "rows": len(formal)
    }])
    if stage == "s2-07a":
        write_csv(root / "start_position_summary.csv", formal)
        write_csv(root / "guaranteed_region_audit.csv", [
            row for row in formal
            if int(row["burstLength"]) <= int(row["correctionCapabilityT"])
        ])
        write_csv(root / "miscorrection_summary.csv", [{
            "caseName": case,
            "miscorrectedPatterns": sum(
                round(float(row["miscorrectionRate"]) * int(row["processedFrames"]))
                for row in formal if row["caseName"] == case
            ),
        } for case in ("BCH-B200", "BCH-B300", "BCH-B300-426")])
    if stage == "s2-07b":
        write_csv(root / "boundary_heatmap_summary.csv", formal)
        write_csv(root / "subblock_error_distribution.csv", formal)
        write_csv(root / "guaranteed_subblock_audit.csv", [
            row for row in formal if row["theoreticalGuaranteedRegion"] == "true"
        ])
    if stage == "s2-07c":
        write_csv(root / "random_start_audit.csv", formal)
        write_csv(root / "confidence_interval_summary.csv", formal)
        write_csv(root / "runtime_summary.csv", formal)
    if stage == "s2-07d":
        write_csv(root / "interleaver_manifest.csv", [
            row for row in formal if row["burstLength"] == "0"
        ])
        write_csv(root / "permutation_hashes.csv", [{
            "caseName": row["caseName"],
            "interleaverMode": row["interleaverMode"],
            "permutationHash": row["permutationHash"],
            "inversePermutationHash": row["inversePermutationHash"],
        } for row in formal if row["burstLength"] == "0"])
        write_csv(root / "error_weight_conservation_audit.csv", formal)
        write_csv(root / "subblock_dispersion_summary.csv", [
            row for row in formal if row["caseName"] in {"BCH-S200", "BCH-S300"}
        ])
        write_csv(root / "paired_comparison_summary.csv", formal)


def execute_stage(repo: Path, executable: Path, stage: str, mode: str) -> None:
    root = repo / "Task/BCH/simulation/stages" / STAGE_DIRS[stage]
    root.mkdir(parents=True, exist_ok=True)
    output = root / f"{mode}_summary.csv"
    run([
        str(executable), "--stage", stage, "--mode", mode,
        "--output", str(output), "--seed", "2026072607", "--progress",
    ], repo)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--stage", choices=STAGE_DIRS)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--formal-only", action="store_true")
    parser.add_argument("--matlab-only", action="store_true")
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-dir")
    parser.add_argument("--checkpoint-every-frames", type=int, default=50)
    parser.add_argument("--stop-after-frames", type=int)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--frame-begin", type=int)
    parser.add_argument("--frame-end", type=int)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--progress-refresh-seconds", type=float, default=1.0)
    parser.add_argument("--clean-local-results", action="store_true")
    parser.add_argument("--skip-matlab", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[4]
    build = repo / "Task/BCH/simulation/build/burst_redesign_mingw"
    executable = build / "bch_burst_runner.exe"
    stages = [args.stage] if args.stage else list(STAGE_DIRS)
    if args.clean_local_results:
        result = repo / "Task/BCH/simulation/results/s2_07_burst_redesign"
        if result.exists():
            shutil.rmtree(result)
    if not (args.plot_only or args.audit_only or args.matlab_only):
        run([
            "cmake", "-G", "MinGW Makefiles",
            "-S", "Task/BCH/simulation/current",
            "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
        ], repo)
        run(["cmake", "--build", str(build), "-j", "4"], repo)
        run([
            "ctest", "--test-dir", str(build), "--output-on-failure",
            "-R", "bch_s2_burst_redesign_unit|bch_s2_impairments_unit",
        ], repo)
        if args.resume:
            run([
                sys.executable,
                "Task/BCH/simulation/scripts/check_bch_s2_burst_resume_shard.py",
            ], repo)
        if not args.formal_only:
            for stage in stages:
                execute_stage(repo, executable, stage, "smoke")
        if not args.smoke_only:
            for stage in stages:
                execute_stage(repo, executable, stage, "formal")
    if args.matlab_only:
        return 0 if run_matlab_reference(
            repo, build, allow_skip=args.skip_matlab) else 2
    matlab_passed = True
    if args.all and not args.smoke_only:
        matlab_passed = run_matlab_reference(
            repo, build, allow_skip=args.skip_matlab)
    if not args.smoke_only:
        for stage in stages:
            derive_stage_files(repo, stage)
            audit_stage(repo, stage)
        if args.stage is None:
            configure_chinese()
            audit_root = repo / (
                "Task/BCH/simulation/stages/s2_07_burst_redesign_audit/figures"
            )
            published = repo / (
                "Task/BCH/simulation/results/s2_07_burst_redesign/published"
            )
            plot_audit = PlotAudit(audit_root, published)
            plot_part_a(repo, plot_audit)
            plot_experiments(repo, plot_audit)
            manifest = {
                "schemaVersion": "bch.s2.burst_redesign.plot_manifest.v1",
                "figureCount": len(plot_audit.records),
                "figures": plot_audit.records,
                "gate": "PASS_BCH_S2_07_BURST_PLOT_AUDIT",
            }
            text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            manifest_path = audit_root.parent / "plot_manifest.json"
            manifest_path.write_text(text, encoding="utf-8")
            (published / "plot_manifest.json").write_text(text, encoding="utf-8")
            write_csv(audit_root.parent / "figure_data_audit.csv", [
                {
                    "filename": item["filename"],
                    "pngSha256": item["pngSha256"],
                    "figureDataSha256": item["figureDataSha256"],
                    "sourceSha256": item["sourceSha256"],
                    "status": "PASS",
                } for item in plot_audit.records
            ])
            print("PASS_BCH_S2_07_BURST_PLOT_AUDIT")
            print("PASS_BCH_S2_07_BURST_STRUCTURE_AND_INTERLEAVING")
            if not matlab_passed:
                print("BLOCKED_BCH_S2_BURST_REDESIGN_AUDIT_INCOMPLETE")
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
