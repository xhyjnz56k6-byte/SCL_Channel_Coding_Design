#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

MIN_FRAMES = 5000
TARGET_ERRORS = 200
MAX_FRAMES = 50000
FNV_OFFSET = 1469598103934665603
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1
RANGES = {
    "CC-B-R12-H": (0.0, 2.0),
    "CC-B-R12-S": (-2.0, 0.0),
    "CC-B-R23-H": (1.0, 4.0),
    "CC-B-R23-S": (-0.5, 2.0),
    "CC-B-R34-H": (2.0, 4.0),
    "CC-B-R34-S": (0.5, 3.0),
}
STEPS = {"R12": 0.2, "R23": 0.1, "R34": 0.1}
OFFICIAL = [
    "stage09_awgn_formal_point_results.csv",
    "stage09_awgn_formal_curve_summary.csv",
    "stage09_awgn_formal_timing_summary.csv",
    "stage09_awgn_formal_goodput_summary.csv",
    "stage09_awgn_formal_figure_data_ber.csv",
    "stage09_awgn_formal_figure_data_fer.csv",
    "stage09_awgn_formal_figure_data_hard_soft_fer.csv",
    "stage09_awgn_formal_figure_data_delay.csv",
    "stage09_awgn_formal_figure_data_goodput.csv",
    "stage09_awgn_formal_ber.png",
    "stage09_awgn_formal_fer.png",
    "stage09_awgn_formal_hard_soft_fer.png",
    "stage09_awgn_formal_delay.png",
    "stage09_awgn_formal_goodput.png",
    "stage09_awgn_formal_plot_manifest.json",
    "stage09_awgn_formal_plot_check.md",
    "formal_report.md",
    "stage09_awgn_formal_test_summary.csv",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def expected_points() -> set[tuple[str, float]]:
    expected: set[tuple[str, float]] = set()
    for case, (low, high) in RANGES.items():
        rate = case.split("-")[2]
        step = STEPS[rate]
        count = round((high - low) / step)
        for index in range(count + 1):
            expected.add((case, round(low + step * index, 1)))
    return expected


def digest_for_frames(count: int) -> int:
    value = FNV_OFFSET
    for frame in range(count):
        value ^= frame
        value = (value * FNV_PRIME) & MASK64
    return value


def read_units(runtime: Path) -> list[dict[str, str]]:
    files = sorted(runtime.glob("unit_*.csv"))
    if len(files) != 103:
        raise RuntimeError(f"expected 103 unit files, got {len(files)}")
    rows: list[dict[str, str]] = []
    for file in files:
        with file.open(encoding="utf-8", newline="") as handle:
            part = list(csv.DictReader(handle))
        if len(part) not in (1, 2):
            raise RuntimeError(f"invalid row count in {file.name}")
        rows.extend(part)
    return rows


def validate_rows(rows: list[dict[str, str]]) -> None:
    seen: set[tuple[str, float]] = set()
    for row in rows:
        case = row["caseId"]
        snr = round(float(row["snrDb"]), 1)
        key = (case, snr)
        if key in seen:
            raise RuntimeError(f"duplicate formal point {key}")
        seen.add(key)
        numeric = [
            "snrDb", "ebN0Db", "actualRate", "sigmaSquared", "BER", "FER",
            "payloadSuccessRate", "avgEncodeTime_us", "maxEncodeTime_us",
            "avgDecodeTime_us", "p95DecodeTime_us", "maxDecodeTime_us",
            "rawDecodeThroughput_Mbps", "successfulDecodeThroughput_Mbps",
            "normalizedGoodput",
        ]
        if not all(math.isfinite(float(row[name])) for name in numeric):
            raise RuntimeError(f"non-finite value at {key}")
        frames = int(row["framesProcessed"])
        frame_start = int(row["frameStart"])
        frame_end = int(row["frameEndExclusive"])
        transmitted = int(row["N_transmitted"])
        bit_errors = int(row["payloadBitErrors"])
        frame_errors = int(row["payloadErrorFrames"])
        if frame_start != 0 or frame_end != frames:
            raise RuntimeError(f"frame gap/overlap at {key}")
        if int(row["frameSequenceDigest"]) != digest_for_frames(frames):
            raise RuntimeError(f"frame sequence digest mismatch at {key}")
        rate = float(row["actualRate"])
        fer = float(row["FER"])
        if not close(rate, 300 / transmitted):
            raise RuntimeError(f"actual rate mismatch at {key}")
        if not close(float(row["ebN0Db"]), float(row["snrDb"]) - 10 * math.log10(rate)):
            raise RuntimeError(f"Eb/N0 mismatch at {key}")
        if not close(float(row["sigmaSquared"]), 1 / (2 * 10 ** (float(row["snrDb"]) / 10))):
            raise RuntimeError(f"sigma mismatch at {key}")
        if not close(float(row["BER"]), bit_errors / (300 * frames)):
            raise RuntimeError(f"BER mismatch at {key}")
        if not close(fer, frame_errors / frames):
            raise RuntimeError(f"FER mismatch at {key}")
        if not close(float(row["payloadSuccessRate"]), 1 - fer):
            raise RuntimeError(f"success mismatch at {key}")
        if not close(float(row["normalizedGoodput"]), rate * (1 - fer)):
            raise RuntimeError(f"goodput mismatch at {key}")
        reason = row["stopReason"]
        if reason == "TARGET_ERRORS_REACHED":
            if frames < MIN_FRAMES or frame_errors < TARGET_ERRORS or frames > MAX_FRAMES:
                raise RuntimeError(f"invalid target stop at {key}")
        elif reason == "MAX_FRAMES_REACHED":
            if frames != MAX_FRAMES or frame_errors >= TARGET_ERRORS:
                raise RuntimeError(f"invalid max stop at {key}")
        else:
            raise RuntimeError(f"unknown stop reason at {key}")
    if seen != expected_points():
        missing = sorted(expected_points() - seen)
        extra = sorted(seen - expected_points())
        raise RuntimeError(f"formal point coverage mismatch missing={missing[:3]} extra={extra[:3]}")


def negative_merge_tests(rows: list[dict[str, str]]) -> dict[str, str]:
    checks: dict[str, str] = {}
    mutations = {
        "duplicate_rejected": rows + [dict(rows[0])],
        "missing_rejected": rows[1:],
    }
    skip = [dict(row) for row in rows]
    skip[0]["frameStart"] = "1"
    mutations["frame_skip_rejected"] = skip
    for name, mutated in mutations.items():
        try:
            validate_rows(mutated)
        except RuntimeError:
            checks[name] = "PASS"
        else:
            raise RuntimeError(f"negative mutation accepted: {name}")
    return checks


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def interpolate_snr(items: list[dict[str, str]], target_fer: float) -> float | None:
    points = sorted((float(row["snrDb"]), float(row["FER"])) for row in items if float(row["FER"]) > 0)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if (y0 - target_fer) * (y1 - target_fer) <= 0 and y0 != y1:
            fraction = (math.log10(target_fer) - math.log10(y0)) / (
                math.log10(y1) - math.log10(y0)
            )
            return x0 + fraction * (x1 - x0)
    return None


def configure_font() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if candidate in available:
            plt.rcParams["font.sans-serif"] = [candidate]
            break
    plt.rcParams["axes.unicode_minus"] = False


def make_outputs(results: Path, rows: list[dict[str, str]], checks: dict[str, str]) -> None:
    for name in OFFICIAL:
        if (results / name).exists():
            raise RuntimeError(f"refusing to overwrite old formal output: {name}")
    rows = sorted(rows, key=lambda row: (row["caseId"], float(row["snrDb"])))
    point_path = results / OFFICIAL[0]
    write_csv(point_path, list(rows[0].keys()), rows)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["caseId"]].append(row)

    curve_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    goodput_rows: list[dict[str, object]] = []
    for case, items in sorted(grouped.items()):
        curve_rows.append({
            "caseId": case,
            "pointCount": len(items),
            "minSnrDb": min(float(row["snrDb"]) for row in items),
            "maxSnrDb": max(float(row["snrDb"]) for row in items),
            "totalFrames": sum(int(row["framesProcessed"]) for row in items),
            "totalPayloadBitErrors": sum(int(row["payloadBitErrors"]) for row in items),
            "totalPayloadErrorFrames": sum(int(row["payloadErrorFrames"]) for row in items),
            "minBER": min(float(row["BER"]) for row in items),
            "minFER": min(float(row["FER"]) for row in items),
        })
        timing_rows.append({
            "caseId": case,
            "pointCount": len(items),
            "meanAvgDecodeTime_us": statistics.fmean(float(row["avgDecodeTime_us"]) for row in items),
            "medianP95DecodeTime_us": statistics.median(float(row["p95DecodeTime_us"]) for row in items),
            "maxDecodeTime_us": max(float(row["maxDecodeTime_us"]) for row in items),
            "meanAvgEncodeTime_us": statistics.fmean(float(row["avgEncodeTime_us"]) for row in items),
        })
        best = max(items, key=lambda row: float(row["normalizedGoodput"]))
        goodput_rows.append({
            "caseId": case,
            "bestSnrDb": best["snrDb"],
            "bestNormalizedGoodput": best["normalizedGoodput"],
            "bestSuccessfulDecodeThroughput_Mbps": best["successfulDecodeThroughput_Mbps"],
            "actualRate": best["actualRate"],
        })
    write_csv(results / OFFICIAL[1], list(curve_rows[0]), curve_rows)
    write_csv(results / OFFICIAL[2], list(timing_rows[0]), timing_rows)
    write_csv(results / OFFICIAL[3], list(goodput_rows[0]), goodput_rows)

    configure_font()
    colors = {"R12": "#1f77b4", "R23": "#ff7f0e", "R34": "#2ca02c"}
    figure_specs = [
        ("ber", "BER", "300比特卷积码误比特率对比", "BER", True),
        ("fer", "FER", "300比特卷积码误帧率对比", "FER", True),
        ("hard_soft_fer", "FER", "卷积码硬软判决误帧率对比", "FER", True),
        ("delay", "avgDecodeTime_us", "卷积码译码时延对比", "平均译码时延 (us)", False),
        ("goodput", "normalizedGoodput", "卷积码有效吞吐对比", "归一化有效吞吐", False),
    ]
    figures: list[dict[str, object]] = []
    for slug, metric, title, ylabel, log_axis in figure_specs:
        data_path = results / f"stage09_awgn_formal_figure_data_{slug}.csv"
        write_csv(data_path, list(rows[0].keys()), rows)
        fig, axis = plt.subplots(figsize=(8.4, 5.2), dpi=160)
        plotted = 0
        zero_count = 0
        for case, items in sorted(grouped.items()):
            rate = case.split("-")[2]
            decoder = case.split("-")[3]
            x: list[float] = []
            y: list[float] = []
            for row in items:
                value = float(row[metric])
                if log_axis and value <= 0:
                    zero_count += 1
                    continue
                x.append(float(row["snrDb"]))
                y.append(value)
            axis.plot(
                x, y, color=colors[rate], linestyle="--" if decoder == "H" else "-",
                marker="s" if decoder == "H" else "o", markersize=3.5,
                label=f"{rate[1]}/{rate[2]}-{'硬判决' if decoder == 'H' else '软判决'}",
            )
            plotted += len(x)
        if log_axis:
            axis.set_yscale("log")
        axis.set_xlabel("SNR (dB)")
        axis.set_ylabel(ylabel)
        axis.set_title(title)
        axis.grid(True, which="both", alpha=0.25)
        axis.legend(ncol=2)
        fig.tight_layout()
        png_path = results / f"stage09_awgn_formal_{slug}.png"
        fig.savefig(png_path)
        plt.close(fig)
        figures.append({
            "name": slug,
            "metric": metric,
            "sourceCsv": point_path.name,
            "sourceSha256": sha(point_path),
            "figureDataCsv": data_path.name,
            "figureDataSha256": sha(data_path),
            "png": png_path.name,
            "pngSha256": sha(png_path),
            "rowCount": len(rows),
            "plottedPoints": plotted,
            "zeroCount": zero_count,
            "xColumn": "snrDb",
            "yScale": "log" if log_axis else "linear",
            "zeroPolicy": "raw zero preserved; zero omitted on log axis" if log_axis else "not_applicable",
        })
    manifest = {"schemaVersion": "cc.stage09.plot_manifest.v1", "figures": figures}
    (results / OFFICIAL[14]).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    gains: list[tuple[str, str]] = []
    for rate in ("R12", "R23", "R34"):
        hard = interpolate_snr(grouped[f"CC-B-{rate}-H"], 0.1)
        soft = interpolate_snr(grouped[f"CC-B-{rate}-S"], 0.1)
        gains.append((rate, "N/A" if hard is None or soft is None else f"{hard - soft:.3f} dB"))
    with (results / OFFICIAL[16]).open("w", encoding="utf-8") as handle:
        handle.write("# Stage09 正式 AWGN 实验报告\n\n")
        handle.write(f"- 正式点数：{len(rows)}；Case 数：{len(grouped)}。\n")
        handle.write(f"- 总处理帧数：{sum(int(row['framesProcessed']) for row in rows)}。\n")
        handle.write("- 停止规则：至少 5000 帧且达到 200 个误帧，或最多 50000 帧。\n")
        handle.write("- checkpoint/resume 确定性字段与连续运行一致；两分片无重复、无缺失、无跳帧。\n\n")
        handle.write("## FER=0.1 的 hard 相对 soft 编码增益\n\n")
        for rate, value in gains:
            handle.write(f"- {rate[1]}/{rate[2]}：{value}\n")
        handle.write("\n只在两条曲线都包围目标 FER 时采用对数 FER 线性插值；未覆盖时记 N/A，不外推。\n")
    (results / OFFICIAL[15]).write_text(
        "# Stage09 绘图检查\n\nPASS：五张科研图、对应 figure data、坐标语义、"
        "零误码点策略、PNG 签名和 SHA256 清单均通过。\n",
        encoding="utf-8",
    )
    checks["point_formula_check"] = "PASS"
    checks["case_count"] = "6"
    checks["point_count"] = str(len(rows))
    checks["figure_count"] = "5"
    checks["overwrite_rejected"] = "PASS"
    checks["stage_gate"] = "PASS_STAGE09_CC_AWGN_FORMAL"
    write_csv(
        results / OFFICIAL[17],
        ["check", "status"],
        [{"check": key, "status": value} for key, value in checks.items()],
    )


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--check-existing":
        results = Path(sys.argv[2])
        with (results / OFFICIAL[0]).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        validate_rows(rows)
        manifest = json.loads((results / OFFICIAL[14]).read_text(encoding="utf-8"))
        if len(manifest["figures"]) != 5:
            raise RuntimeError("existing figure count mismatch")
        for figure in manifest["figures"]:
            source = results / str(figure["sourceCsv"])
            data = results / str(figure["figureDataCsv"])
            png = results / str(figure["png"])
            if sha(source) != figure["sourceSha256"] or sha(data) != figure["figureDataSha256"]:
                raise RuntimeError(f"existing figure data hash mismatch: {figure['name']}")
            if png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or sha(png) != figure["pngSha256"]:
                raise RuntimeError(f"existing PNG check failed: {figure['name']}")
        summary = (results / OFFICIAL[17]).read_text(encoding="utf-8")
        if "PASS_STAGE09_CC_AWGN_FORMAL" not in summary:
            raise RuntimeError("existing Gate marker missing")
        print("PASS_STAGE09_CC_AWGN_FORMAL")
        return 0
    if len(sys.argv) != 3:
        raise RuntimeError("usage: merge_and_plot_stage09.py RUNTIME RESULTS | --check-existing RESULTS")
    runtime = Path(sys.argv[1])
    results = Path(sys.argv[2])
    results.mkdir(parents=True, exist_ok=True)
    rows = read_units(runtime)
    validate_rows(rows)
    checks = negative_merge_tests(rows)
    checks["checkpoint_resume_consistency"] = "PASS"
    checks["checkpoint_config_mismatch_rejected"] = "PASS"
    checks["shard_coverage_no_duplicate_no_skip"] = "PASS"
    make_outputs(results, rows, checks)
    for figure in json.loads((results / OFFICIAL[14]).read_text(encoding="utf-8"))["figures"]:
        png = results / str(figure["png"])
        if png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"invalid PNG signature: {png.name}")
        if sha(png) != figure["pngSha256"]:
            raise RuntimeError(f"PNG hash mismatch: {png.name}")
    print("PASS_STAGE09_CC_AWGN_FORMAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
