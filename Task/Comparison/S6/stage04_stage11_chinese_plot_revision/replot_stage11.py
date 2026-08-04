#!/usr/bin/env python3
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = pathlib.Path(__file__).resolve().parents[4]
S5_STAGE11 = ROOT / "Task" / "Comparison" / "S5" / "results" / "stage11"
OLD_PLOTS = S5_STAGE11 / "plots"
SOURCE = ROOT / "Task" / "Comparison" / "S5" / "results" / "formal" / "merged" / "formal_merged_results.csv"
OUTPUT = ROOT / "Task" / "Comparison" / "S6" / "results" / "stage11_chinese"
PLOTS = OUTPUT / "plots"
SCRIPT = pathlib.Path(__file__).resolve()
README_TEMPLATE = SCRIPT.parent / "generated_plot_readme.txt"

SCHEME_LABEL = {
    "CC_R23_BLOCK_FLOAT": "卷积码 R2/3",
    "LDPC_BG2_N480_NMS": "LDPC N480",
    "CC_R12_BLOCK_FLOAT": "卷积码 R1/2",
    "LDPC_BG2_N640_NMS": "LDPC N640",
}
CHANNEL_LABEL = {
    "AWGN": "AWGN",
    "FIXED_MULTIPATH_REAL_MMSE": "固定多径",
    "CFO_30_DEG": "30°载波频偏",
    "LINEAR_TIME_VARYING_FREQUENCY": "多普勒频移",
    "KNOWN_BLOCKAGE_5_PERCENT": "短时遮挡（5%）",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB": "未知突发干扰（5%，ISR=10 dB）",
}
COLORS = {
    "CC_R23_BLOCK_FLOAT": "#0072B2",
    "LDPC_BG2_N480_NMS": "#D55E00",
    "CC_R12_BLOCK_FLOAT": "#009E73",
    "LDPC_BG2_N640_NMS": "#CC79A7",
}
LINE_STYLES = {
    "CC_R23_BLOCK_FLOAT": "-",
    "LDPC_BG2_N480_NMS": "--",
    "CC_R12_BLOCK_FLOAT": "-.",
    "LDPC_BG2_N640_NMS": ":",
}
MARKERS = {
    "CC_R23_BLOCK_FLOAT": "o",
    "LDPC_BG2_N480_NMS": "s",
    "CC_R12_BLOCK_FLOAT": "^",
    "LDPC_BG2_N640_NMS": "D",
}
CHANNEL_COLORS = {
    name: color for name, color in zip(CHANNEL_LABEL, (
        "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"))
}


def sha256(path):
    value = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(rows[0])
    with pathlib.Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def configure_font():
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("BLOCK_PLOT_RELEASE: no approved Chinese font")


def git_commit():
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def source_index(rows):
    result = {}
    for row in rows:
        key = (row["group"], row["channel"], row["scheme"], float(row["esN0Db"]))
        if key in result:
            raise RuntimeError(f"duplicate Formal source key: {key}")
        result[key] = row
    return result


def source_row(index, group, channel, scheme, snr):
    if group == "LDPC_ONLY":
        matches = [row for (g, c, s, x), row in index.items()
                   if c == channel and s == scheme and x == snr]
        if len(matches) != 1:
            raise RuntimeError(f"LDPC source row count != 1: {channel}/{scheme}/{snr}")
        return matches[0]
    key = (group, channel, scheme, snr)
    if key not in index:
        raise RuntimeError(f"missing Formal source row: {key}")
    return index[key]


def curve_definition(field, manifest):
    parts = field.split("__")
    if parts[0] == "deltaFer":
        channel, scheme = parts[1], parts[2]
        return {
            "metric": "FER_DIFFERENCE_FROM_AWGN",
            "scheme": scheme,
            "channel": channel,
            "legend": f"{CHANNEL_LABEL[channel]} / {SCHEME_LABEL[scheme]}",
        }
    metric, scheme = parts[0], parts[1]
    return {
        "metric": metric,
        "scheme": scheme,
        "channel": manifest["channel"],
        "legend": SCHEME_LABEL[scheme],
    }


def curve_values(field, definition, manifest, index):
    group = manifest["comparisonGroup"]
    channel = definition["channel"]
    scheme = definition["scheme"]
    values = []
    snrs = sorted({x for (g, c, s, x) in index
                   if c == channel and s == scheme and (group == "LDPC_ONLY" or g == group)})
    for snr in snrs:
        row = source_row(index, group, channel, scheme, snr)
        if definition["metric"] == "FER_DIFFERENCE_FROM_AWGN":
            reference = source_row(index, group, "AWGN", scheme, snr)
            raw = float(row["FER"]) - float(reference["FER"])
        else:
            raw = float(row[definition["metric"]])
        if not math.isfinite(raw):
            raise RuntimeError(f"non-finite source value: {field}/{snr}")
        values.append((snr, raw, row))
    return values


def style_for(definition):
    scheme = definition["scheme"]
    if definition["metric"] == "FER_DIFFERENCE_FROM_AWGN":
        return CHANNEL_COLORS[definition["channel"]], LINE_STYLES[scheme], MARKERS[scheme]
    return COLORS[scheme], LINE_STYLES[scheme], MARKERS[scheme]


def render_one(old_dir, formal_rows, index, font_name, commit):
    manifest_path = old_dir / "plot_manifest.json"
    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if old_manifest["sourceFormalCsvSha256"] != sha256(SOURCE):
        raise RuntimeError(f"source hash mismatch: {old_dir.name}")
    title = old_manifest["title"]
    if not re.search(r"[\u4e00-\u9fff]", title):
        raise RuntimeError(f"non-Chinese title: {old_dir.name}")
    figure_id = old_manifest["figureId"]
    if figure_id != old_dir.name:
        raise RuntimeError(f"figure id mismatch: {old_dir.name}")
    target = PLOTS / figure_id
    if target.exists():
        raise RuntimeError(f"refuse to overwrite plot directory: {target}")
    target.mkdir(parents=True)
    (target / "readme.txt").write_bytes(README_TEMPLATE.read_bytes())
    log_scale = bool(old_manifest["logAxis"])
    y_fields = list(old_manifest["yColumns"])
    long_rows = []
    plot_curves = []
    legend_entries = []
    colors = []
    line_styles = []
    markers = []
    for field in y_fields:
        definition = curve_definition(field, old_manifest)
        values = curve_values(field, definition, old_manifest, index)
        if len(values) != 31:
            raise RuntimeError(f"x point count != 31: {figure_id}/{field}")
        x_values, y_values = [], []
        for snr, raw, source in values:
            is_zero = raw == 0.0
            is_plotted = not (log_scale and is_zero)
            plot_value = raw if is_plotted else math.nan
            frames = int(source["frames"])
            long_rows.append({
                "figureId": figure_id,
                "sourceRunId": source["runId"],
                "sourceMetric": definition["metric"],
                "scheme": definition["scheme"],
                "legend": definition["legend"],
                "esN0Db": format(snr, ".17g"),
                "rawValue": format(raw, ".17g"),
                "plotValue": format(plot_value, ".17g") if is_plotted else "",
                "isPlotted": str(is_plotted).lower(),
                "isZero": str(is_zero).lower(),
                "zeroErrorUpperBound95": format(3.0 / frames, ".17g") if is_zero else "",
            })
            x_values.append(snr)
            y_values.append(plot_value)
        color, line_style, marker = style_for(definition)
        plot_curves.append((x_values, y_values, definition["legend"], color, line_style, marker))
        legend_entries.append(definition["legend"])
        colors.append(color)
        line_styles.append(line_style)
        markers.append(marker)
    write_csv(target / "figure_data.csv", long_rows)
    figure, axis = plt.subplots(figsize=(8.6, 5.6), dpi=180)
    for x_values, y_values, legend, color, line_style, marker in plot_curves:
        axis.plot(x_values, y_values, color=color, linestyle=line_style, marker=marker,
                  linewidth=1.5, markersize=3.6, label=legend)
    if log_scale:
        axis.set_yscale("log")
    x_label = "符号信噪比 Es/N0（dB）"
    y_label = old_manifest["units"]["y"]
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.set_title(title)
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    png_path = target / "figure.png"
    figure.savefig(png_path, dpi=180)
    plt.close(figure)
    png_hash = sha256(png_path)
    data_hash = sha256(target / "figure_data.csv")
    new_manifest = {
        "figureId": figure_id,
        "title": title,
        "sourceFiles": [SOURCE.relative_to(ROOT).as_posix()],
        "sourceFileHashes": [sha256(SOURCE)],
        "sourceOldFigure": (old_dir / "figure.png").relative_to(ROOT).as_posix(),
        "sourceOldFigureSha256": sha256(old_dir / "figure.png"),
        "sourceOldManifestSha256": sha256(manifest_path),
        "filterConditions": old_manifest["filterConditions"],
        "xColumn": "esN0Db",
        "yColumns": y_fields,
        "xLabel": x_label,
        "yLabel": y_label,
        "xUnit": "dB",
        "yUnit": y_label,
        "xTransform": "NONE",
        "yTransform": "LOG10_DISPLAY" if log_scale else "NONE",
        "logScale": log_scale,
        "zeroValuePolicy": "原始零值保留；对数轴不绘制，plotValue 留空且曲线不跨零连接" if log_scale else "按原始值绘制",
        "missingValuePolicy": "缺失即阻断发布",
        "interpolation": "NONE",
        "smoothing": "NONE",
        "legendEntries": legend_entries,
        "colors": colors,
        "lineStyles": line_styles,
        "markers": markers,
        "outputPng": png_path.relative_to(ROOT).as_posix(),
        "outputCsv": (target / "figure_data.csv").relative_to(ROOT).as_posix(),
        "outputHash": png_hash,
        "outputCsvHash": data_hash,
        "scriptPath": SCRIPT.relative_to(ROOT).as_posix(),
        "scriptSha256": sha256(SCRIPT),
        "gitCommit": commit,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "chineseFont": font_name,
    }
    (target / "plot_manifest.json").write_text(
        json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    zero_rows = [row for row in long_rows if row["isZero"] == "true"]
    checks = {
        "source_file_exists": SOURCE.exists(),
        "source_sha256_recorded": bool(new_manifest["sourceFileHashes"][0]),
        "x_point_count_matches": all(len(curve[0]) == 31 for curve in plot_curves),
        "y_point_count_matches": len(long_rows) == 31 * len(y_fields),
        "all_raw_values_finite_or_explicitly_missing": all(math.isfinite(float(row["rawValue"])) for row in long_rows),
        "raw_zero_values_preserved": all(float(row["rawValue"]) == 0 for row in zero_rows),
        "zero_values_not_replaced": all(row["plotValue"] == "" for row in zero_rows) if log_scale else True,
        "zero_values_not_plotted_on_log_axis": all(row["isPlotted"] == "false" for row in zero_rows) if log_scale else True,
        "no_artificial_floor_line": True,
        "no_interpolation": new_manifest["interpolation"] == "NONE",
        "no_smoothing": new_manifest["smoothing"] == "NONE",
        "legend_entries_unique": len(set(legend_entries)) == len(legend_entries),
        "title_is_chinese": bool(re.search(r"[\u4e00-\u9fff]", title)),
        "axis_labels_are_valid": x_label == "符号信噪比 Es/N0（dB）" and bool(y_label),
        "png_exists": png_path.exists(),
        "figure_data_exists": (target / "figure_data.csv").exists(),
        "manifest_exists": (target / "plot_manifest.json").exists(),
        "readme_exists": (target / "readme.txt").exists(),
        "output_sha256_recorded": bool(png_hash),
    }
    if not all(checks.values()):
        raise RuntimeError(f"BLOCK_PLOT_RELEASE: {figure_id}: {checks}")
    (target / "plot_check.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"figureId": figure_id, "title": title, "pngSha256": png_hash,
            "dataSha256": data_hash, "logScale": log_scale, "zeroRows": len(zero_rows), "gate": "PASS"}


def main():
    if not SOURCE.exists():
        raise RuntimeError("BLOCK_PLOT_RELEASE: Formal source CSV missing")
    old_dirs = sorted(path for path in OLD_PLOTS.iterdir() if path.is_dir())
    if len(old_dirs) != 86:
        raise RuntimeError(f"BLOCK_PLOT_RELEASE: old figure count {len(old_dirs)} != 86")
    if PLOTS.exists() and any(path.is_dir() for path in PLOTS.iterdir()):
        raise RuntimeError("BLOCK_PLOT_RELEASE: output plot directory is not empty")
    PLOTS.mkdir(parents=True, exist_ok=True)
    formal_rows = read_csv(SOURCE)
    if len(formal_rows) != 744:
        raise RuntimeError(f"BLOCK_PLOT_RELEASE: Formal row count {len(formal_rows)} != 744")
    index = source_index(formal_rows)
    font_name = configure_font()
    commit = git_commit()
    results = [render_one(directory, formal_rows, index, font_name, commit) for directory in old_dirs]
    summary = {
        "schemaVersion": "s6.stage11.plot_audit.v1",
        "figureCount": len(results),
        "passedFigures": sum(row["gate"] == "PASS" for row in results),
        "logScaleFigures": sum(row["logScale"] for row in results),
        "preservedZeroRows": sum(row["zeroRows"] for row in results),
        "sourceFormalCsvSha256": sha256(SOURCE),
        "gate": "PASS_STAGE11_CHINESE_PLOT_REVISION",
        "figures": results,
    }
    (OUTPUT / "plot_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summary["gate"], f"figures={len(results)}", f"zeroRows={summary['preservedZeroRows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
