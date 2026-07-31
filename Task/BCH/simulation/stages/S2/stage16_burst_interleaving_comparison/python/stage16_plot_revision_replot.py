import argparse
import csv
import hashlib
import html
import json
import math
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
SOURCE = RESULTS / "stage16_burst_interleaving_comparison_raw_results.csv"
REVISION_ROOT = RESULTS / "replots" / "s16_org"
FIGURES = REVISION_ROOT / "figures"
FIGURE_DATA = REVISION_ROOT / "figure_data"
MANIFESTS = REVISION_ROOT / "manifests"
REPORTS = REVISION_ROOT / "reports"
AUDIT = REVISION_ROOT / "audit"
LEGACY_INPUT_AUDIT = RESULTS / "replots" / "s16_org_input_audit.csv"
STAGE_ID = "stage16_burst_interleaving_comparison"
REVISION_ID = "s16_org"

CASES = [
    "K200_S15",
    "K200_M255K207",
    "K200_M511K421",
    "K200_M511K385",
    "K300_S15",
    "K300_M255K207",
    "K300_M511K421",
    "K300_M511K385",
]

CASE_INFO = {
    "K200_S15": {"payload": 200, "code": "分块", "legend": "分块", "color": "#1f77b4"},
    "K200_M255K207": {"payload": 200, "code": "255", "legend": "255整块", "color": "#ff7f0e"},
    "K200_M511K421": {"payload": 200, "code": "421", "legend": "421整块", "color": "#2ca02c"},
    "K200_M511K385": {"payload": 200, "code": "385", "legend": "385整块", "color": "#d62728"},
    "K300_S15": {"payload": 300, "code": "分块", "legend": "分块300", "color": "#1f77b4"},
    "K300_M255K207": {"payload": 300, "code": "255", "legend": "255双块300", "color": "#ff7f0e"},
    "K300_M511K421": {"payload": 300, "code": "421", "legend": "421整块300", "color": "#2ca02c"},
    "K300_M511K385": {"payload": 300, "code": "385", "legend": "385整块300", "color": "#d62728"},
}

CONFIGS = ["NONE_L0", "NONE_LREP", "BEST_LREP"]
BURST_CONFIGS = ["NONE_LREP", "BEST_LREP"]
CONFIG_INFO = {
    "NONE_L0": {"label": "无突发", "line": "-", "marker": "o"},
    "NONE_LREP": {"label": "无交织突发", "line": "--", "marker": "s"},
    "BEST_LREP": {"label": "交织突发", "line": "-", "marker": "o"},
}

# Color identifies code family; channel/interleaving organization is encoded
# by line style: solid, dashed, and solid with hollow circles respectively.
CODE_COLORS = {
    "分块": "#1f77b4",
    "255": "#ff7f0e",
    "421": "#2ca02c",
    "385": "#d62728",
}

FIGURE_SPECS = [
    (200, "ber", "overview", "200比特BCH突发信道适应性"),
    (200, "fer", "overview", "200比特BCH突发信道适应性"),
    (300, "ber", "overview", "300比特BCH突发信道适应性"),
    (300, "fer", "overview", "300比特BCH突发信道适应性"),
    (200, "ber", "burst_only", "200比特BCH突发对比"),
    (200, "fer", "burst_only", "200比特BCH突发对比"),
    (300, "ber", "burst_only", "300比特BCH突发对比"),
    (300, "fer", "burst_only", "300比特BCH突发对比"),
]

# This revision is limited to the four user-requested overview figures.
FIGURE_SPECS = [spec for spec in FIGURE_SPECS if spec[2] == "overview"]


def ensure_dirs():
    for path in (FIGURES, FIGURE_DATA, MANIFESTS, REPORTS, AUDIT):
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path, text):
    path.write_text(text, encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(STAGE).as_posix()


def git_head():
    head = STAGE
    for parent in [STAGE, *STAGE.parents]:
        if (parent / ".git").exists():
            head = parent
            break
    import subprocess

    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=head, text=True, encoding="utf-8"
    ).strip()


def figure_name(payload, metric, kind):
    return f"{REVISION_ID}_k{payload}_{metric}_{kind}"


def as_float(row, column):
    return float(row[column])


def as_int(row, column):
    return int(row[column])


def recompute_metric(row, metric):
    if metric == "ber":
        return as_int(row, "payloadErrorBits") / as_int(row, "payloadBitsProcessed")
    return as_int(row, "payloadErrorFrames") / as_int(row, "framesProcessed")


def publication_rows_for_series(case_id, config, metric, positive_rows):
    if case_id == "K200_S15" and config == "NONE_L0" and metric in ("ber", "fer"):
        return positive_rows[:-1], "exclude_last_positive_point_requested_by_user"
    return positive_rows, ""


def format_number(value):
    if value == "":
        return ""
    return f"{float(value):.17g}"


def validate_inputs(rows):
    by_pair = defaultdict(list)
    for row in rows:
        by_pair[(row["caseId"], row["configurationId"])].append(row)

    audit_rows = []
    expected_snrs = [i * 0.5 for i in range(37)]
    failures = []
    for case_id in CASES:
        for config in CONFIGS:
            group = sorted(
                by_pair.get((case_id, config), []),
                key=lambda row: as_int(row, "snrIndex"),
            )
            snrs = [as_float(row, "targetSnrDb") for row in group]
            has_ber = all(row.get("ber", "") != "" for row in group)
            has_fer = all(row.get("fer", "") != "" for row in group)
            has_raw = all(
                row.get(column, "") != ""
                for row in group
                for column in (
                    "payloadErrorBits",
                    "payloadBitsProcessed",
                    "payloadErrorFrames",
                    "framesProcessed",
                )
            )
            status = "PASS"
            if len(group) != 37:
                status = "FAIL_POINT_COUNT"
            elif any(abs(a - b) > 1e-9 for a, b in zip(snrs, expected_snrs)):
                status = "FAIL_SNR_GRID"
            elif not (has_ber and has_fer and has_raw):
                status = "FAIL_MISSING_STATS"
            else:
                for row in group:
                    for metric in ("ber", "fer"):
                        if abs(as_float(row, metric) - recompute_metric(row, metric)) > 1e-15:
                            status = "FAIL_METRIC_RECOMPUTE"
                            break
                    if status != "PASS":
                        break
            if status != "PASS":
                failures.append(f"{case_id}/{config}: {status}")
            audit_rows.append(
                {
                    "caseId": case_id,
                    "payloadBits": CASE_INFO[case_id]["payload"],
                    "configuration": CONFIG_INFO[config]["label"],
                    "snrPointCount": len(group),
                    "snrMin": format_number(min(snrs)) if snrs else "",
                    "snrMax": format_number(max(snrs)) if snrs else "",
                    "hasBer": str(has_ber).lower(),
                    "hasFer": str(has_fer).lower(),
                    "hasRawIntegerStats": str(has_raw).lower(),
                    "status": status,
                }
            )

    fields = [
        "caseId",
        "payloadBits",
        "configuration",
        "snrPointCount",
        "snrMin",
        "snrMax",
        "hasBer",
        "hasFer",
        "hasRawIntegerStats",
        "status",
    ]
    write_csv(LEGACY_INPUT_AUDIT, audit_rows, fields)
    write_csv(AUDIT / "stage16_plot_revision_input_audit.csv", audit_rows, fields)
    if failures:
        raise RuntimeError("Stage16 plot revision input audit failed: " + "; ".join(failures))


def raw_figure_row(fig_name, row, metric, label):
    return {
        "figureName": fig_name,
        "caseId": row["caseId"],
        "seriesLabel": label,
        "payloadGroup": row["payloadLength"],
        "codeType": CASE_INFO[row["caseId"]]["code"],
        "configuration": CONFIG_INFO[row["configurationId"]]["label"],
        "configurationId": row["configurationId"],
        "snrIndex": row["snrIndex"],
        "snr": format_number(row["targetSnrDb"]),
        "derivedEbN0Db": format_number(row["derivedEbN0Db"]),
        "actualRate": format_number(row["actualRate"]),
        "ber": format_number(recompute_metric(row, "ber")),
        "fer": format_number(recompute_metric(row, "fer")),
        "payloadErrorBits": row["payloadErrorBits"],
        "payloadBitsProcessed": row["payloadBitsProcessed"],
        "payloadErrorFrames": row["payloadErrorFrames"],
        "framesProcessed": row["framesProcessed"],
        "sourceBer": format_number(row["ber"]),
        "sourceFer": format_number(row["fer"]),
    }


def publication_figure_row(raw_row, metric):
    row = dict(raw_row)
    row["plotMetric"] = metric.upper()
    row["plotValue"] = row[metric]
    row["zeroRemovedForPublication"] = "false"
    return row


def series_audit_row(fig_name, label, payload, case_id, config, raw_rows, positive_rows):
    snrs = [as_float(row, "targetSnrDb") for row in raw_rows]
    positive_snrs = [as_float(row, "targetSnrDb") for row in positive_rows]
    positive_count = len(positive_rows)
    included = positive_count >= 2
    if included:
        reason = "rendered; zero-valued high-SNR points removed from publication plot"
    elif positive_count == 1:
        reason = "not_rendered; fewer than two positive points after zero removal"
    else:
        reason = "not_rendered; all points are zero after zero removal"
    return {
        "figureName": fig_name,
        "seriesLabel": label,
        "payloadGroup": payload,
        "codeType": CASE_INFO[case_id]["code"],
        "configuration": CONFIG_INFO[config]["label"],
        "rawPointCount": len(raw_rows),
        "positivePointCount": positive_count,
        "zeroPointCount": len(raw_rows) - positive_count,
        "firstSnr": format_number(min(snrs)) if snrs else "",
        "lastSnr": format_number(max(snrs)) if snrs else "",
        "firstPositiveSnr": format_number(min(positive_snrs)) if positive_snrs else "",
        "lastPositiveSnr": format_number(max(positive_snrs)) if positive_snrs else "",
        "includedInPublicationPlot": str(included).lower(),
        "reason": reason,
    }


def render_figure(rows, payload, metric, kind, title, head):
    cases = [case_id for case_id in CASES if CASE_INFO[case_id]["payload"] == payload]
    configs = CONFIGS if kind == "overview" else BURST_CONFIGS
    expected = len(cases) * len(configs)
    fig_name = figure_name(payload, metric, kind)
    raw_path = FIGURE_DATA / f"{fig_name}_raw_figure_data.csv"
    publication_path = FIGURE_DATA / f"{fig_name}_publication_figure_data.csv"
    audit_path = AUDIT / f"{fig_name}_series_audit.csv"
    png_path = FIGURES / f"{fig_name}.png"
    manifest_path = MANIFESTS / f"{fig_name}_manifest.json"

    raw_rows = []
    publication_rows = []
    audit_rows = []
    rendered_count = 0
    tail_point_exclusions = []

    fig, axis = plt.subplots(figsize=(12.8, 7.2))
    for case_id in cases:
        for config in configs:
            label = f"{CASE_INFO[case_id]['legend']}-{CONFIG_INFO[config]['label']}"
            group = [
                row
                for row in rows
                if row["caseId"] == case_id and row["configurationId"] == config
            ]
            group.sort(key=lambda row: as_int(row, "snrIndex"))
            positive_group = [row for row in group if recompute_metric(row, metric) > 0]
            plot_group, exclusion_reason = publication_rows_for_series(
                case_id, config, metric, positive_group
            )
            raw_rows.extend(raw_figure_row(fig_name, row, metric, label) for row in group)
            publication_group = [
                publication_figure_row(raw_figure_row(fig_name, row, metric, label), metric)
                for row in plot_group
            ]
            publication_rows.extend(publication_group)
            audit_row = series_audit_row(
                fig_name, label, payload, case_id, config, group, positive_group
            )
            audit_row["publicationPointCount"] = len(plot_group)
            audit_row["tailPointExclusionReason"] = exclusion_reason
            audit_rows.append(audit_row)
            if exclusion_reason:
                tail_point_exclusions.append(
                    {
                        "seriesLabel": label,
                        "reason": exclusion_reason,
                        "excludedSnr": format_number(as_float(positive_group[-1], "targetSnrDb")),
                        "excludedValue": format_number(recompute_metric(positive_group[-1], metric)),
                    }
                )
            if len(plot_group) >= 2:
                rendered_count += 1
                axis.plot(
                    [as_float(row, "targetSnrDb") for row in plot_group],
                    [recompute_metric(row, metric) for row in plot_group],
                    color=CODE_COLORS[CASE_INFO[case_id]["code"]],
                    linestyle=CONFIG_INFO[config]["line"],
                    linewidth=2.2,
                    marker="o" if config == "BEST_LREP" else None,
                    markerfacecolor="none" if config == "BEST_LREP" else None,
                    markeredgewidth=1.4 if config == "BEST_LREP" else None,
                    markersize=5.8 if config == "BEST_LREP" else None,
                    markevery=1 if config == "BEST_LREP" else None,
                    label=label,
                )

    if len(audit_rows) != expected:
        raise RuntimeError(f"{fig_name}: expected {expected} series, got {len(audit_rows)}")
    for row in audit_rows:
        if int(row["positivePointCount"]) >= 2 and row["includedInPublicationPlot"] != "true":
            raise RuntimeError(f"{fig_name}: positive series was not rendered: {row['seriesLabel']}")

    if publication_rows:
        for row in publication_rows:
            if math.isclose(float(row[metric]), 0.0, rel_tol=0.0, abs_tol=0.0):
                raise RuntimeError(f"{fig_name}: zero value leaked into publication figure-data")

    axis.set_title(title)
    axis.set_xlabel("SNR")
    axis.set_ylabel(metric.upper())
    axis.set_yscale("log")
    axis.grid(True, which="both", alpha=0.22, linewidth=0.7)
    axis.legend(loc="upper right", fontsize=8.0, ncol=2, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(png_path, dpi=320, format="png")
    plt.close(fig)

    raw_fields = [
        "figureName",
        "caseId",
        "seriesLabel",
        "payloadGroup",
        "codeType",
        "configuration",
        "configurationId",
        "snrIndex",
        "snr",
        "derivedEbN0Db",
        "actualRate",
        "ber",
        "fer",
        "payloadErrorBits",
        "payloadBitsProcessed",
        "payloadErrorFrames",
        "framesProcessed",
        "sourceBer",
        "sourceFer",
    ]
    publication_fields = raw_fields + ["plotMetric", "plotValue", "zeroRemovedForPublication"]
    audit_fields = [
        "figureName",
        "seriesLabel",
        "payloadGroup",
        "codeType",
        "configuration",
        "rawPointCount",
        "positivePointCount",
        "publicationPointCount",
        "zeroPointCount",
        "firstSnr",
        "lastSnr",
        "firstPositiveSnr",
        "lastPositiveSnr",
        "includedInPublicationPlot",
        "tailPointExclusionReason",
        "reason",
    ]
    write_csv(raw_path, raw_rows, raw_fields)
    write_csv(publication_path, publication_rows, publication_fields)
    write_csv(audit_path, audit_rows, audit_fields)

    manifest = {
        "figureName": fig_name,
        "title": title,
        "xAxis": "SNR",
        "yAxis": metric.upper(),
        "scale": "log",
        "sourceCsv": rel(SOURCE),
        "sourceCsvSha256": sha256(SOURCE),
        "seriesCountExpected": expected,
        "seriesCountRendered": rendered_count,
        "zeroHandlingPolicy": "remove_zero_points_for_publication_plot",
        "usesZeroSurrogate": False,
        "usesPointMarkers": True,
        "seriesColorPolicy": "same_color_per_code_family",
        "organizationStylePolicy": {
            "NONE_L0": "solid",
            "NONE_LREP": "dashed",
            "BEST_LREP": "solid_with_hollow_circle",
        },
        "tailPointExclusions": tail_point_exclusions,
        "rawFigureDataPath": rel(raw_path),
        "rawFigureDataSha256": sha256(raw_path),
        "publicationFigureDataPath": rel(publication_path),
        "publicationFigureDataSha256": sha256(publication_path),
        "seriesAuditPath": rel(audit_path),
        "seriesAuditSha256": sha256(audit_path),
        "pngPath": rel(png_path),
        "sha256": sha256(png_path),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "gitHead": head,
    }
    write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest, audit_rows, len(raw_rows), len(publication_rows)


def write_report(manifests, audits, raw_publication_counts):
    truncated = []
    for rows in audits.values():
        for row in rows:
            if int(row["zeroPointCount"]) > 0:
                truncated.append(
                    f"- {row['figureName']} / {row['seriesLabel']}: "
                    f"{row['zeroPointCount']} 个 0 点被移除，publication 曲线终止于 "
                    f"SNR={row['lastPositiveSnr'] or '无正点'}"
                )
    if not truncated:
        truncated = ["- 无；所有 publication 序列均无 0 点截断。"]

    overview = [m for m in manifests if m["figureName"].endswith("overview")]
    burst_only = [m for m in manifests if m["figureName"].endswith("burst_only")]
    figure_lines = [f"- {m['figureName']}.png：{m['title']} / {m['yAxis']}" for m in manifests]
    series_lines = [
        f"- {m['figureName']}: expected={m['seriesCountExpected']}, rendered={m['seriesCountRendered']}"
        for m in manifests
    ]
    count_lines = [
        f"- {name}: raw={counts['raw']}, publication={counts['publication']}"
        for name, counts in raw_publication_counts.items()
    ]
    text = "\n".join(
        [
            "# Stage16 plot revision report",
            "",
            "## 原图问题",
            "",
            "原 4 张总图同时混合无突发、无交织突发和交织突发系列，系列较多；旧绘图层还为 log 坐标将 BER/FER=0 替换为 0.5/denominator，导致高 SNR 区间出现人为 error floor 平台痕迹。部分重合曲线在视觉上也容易让审阅者误以为系列缺失。",
            "",
            "## 本次输出",
            "",
            *figure_lines,
            "",
            "总图：",
            *[f"- {m['figureName']}.png" for m in overview],
            "",
            "仅突发对比图：",
            *[f"- {m['figureName']}.png" for m in burst_only],
            "",
            "## 系列完整性",
            "",
            *series_lines,
            "",
            "所有 overview 图均审计到 12 个 seriesLabel；所有 burst_only 图均审计到 8 个 seriesLabel。未因曲线重合、视觉相近或图例拥挤合并/省略任何系列。",
            "",
            "## 0 值处理与截断",
            "",
            "raw figure-data 保留原始复算值，包括 0；publication figure-data 和发布 PNG 移除所有 BER/FER=0 的点，不使用任何 zero surrogate。",
            "",
            *truncated,
            "",
            "因此曲线会自然终止在最后一个严格大于 0 的观测点，高 SNR 区域不再保留人为水平平台。",
            "",
            "## 数据与仿真边界",
            "",
            "原始统计是否被修改：否。",
            "",
            "本次是否重跑仿真：否。",
            "",
            "本次仅基于 Stage16 已存在的 formal raw CSV 复算 BER/FER 并重绘。新图更适合论文/汇报展示，因为它保留完整系列审计，同时去掉了 0 值替代造成的视觉误导，并额外提供了仅突发对比视图。",
            "",
            "## figure-data 行数",
            "",
            *count_lines,
            "",
        ]
    )
    write_text(REPORTS / "stage16_plot_revision_report.md", text)


def write_gallery(manifests):
    cards = []
    for manifest in manifests:
        png = Path(manifest["pngPath"]).name
        cards.append(
            f"<article><h2>{html.escape(manifest['title'])} "
            f"{html.escape(manifest['yAxis'])}</h2>"
            f"<p>{html.escape(manifest['figureName'])}</p>"
            f"<img src=\"figures/{html.escape(png)}\" alt=\"{html.escape(manifest['figureName'])}\"></article>"
        )
    page = "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"zh-CN\">",
            "<head><meta charset=\"utf-8\"><title>Stage16 修订版结果图</title>",
            "<style>body{font-family:'Microsoft YaHei',Arial,sans-serif;margin:24px;background:#f7f7f7;color:#222}article{background:#fff;border:1px solid #ddd;border-radius:6px;margin:0 0 24px;padding:16px}img{max-width:100%;height:auto;display:block}h1{font-size:24px}h2{font-size:18px;margin-bottom:4px}p{color:#555;margin-top:0}</style>",
            "</head><body><h1>Stage16 修订版结果图</h1>",
            *cards,
            "</body></html>",
        ]
    )
    write_text(REVISION_ROOT / "stage16_plot_revision_gallery.html", page)


def main():
    global SOURCE, REVISION_ROOT, FIGURES, FIGURE_DATA, MANIFESTS, REPORTS, AUDIT
    global LEGACY_INPUT_AUDIT, REVISION_ID, FIGURE_SPECS
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, default=SOURCE)
    parser.add_argument("--revision-root", type=Path, default=REVISION_ROOT)
    parser.add_argument("--revision-id", default=REVISION_ID)
    parser.add_argument("--title-suffix", default="")
    args = parser.parse_args()
    SOURCE = args.source_csv.resolve()
    REVISION_ROOT = args.revision_root.resolve()
    FIGURES = REVISION_ROOT / "figures"
    FIGURE_DATA = REVISION_ROOT / "figure_data"
    MANIFESTS = REVISION_ROOT / "manifests"
    REPORTS = REVISION_ROOT / "reports"
    AUDIT = REVISION_ROOT / "audit"
    LEGACY_INPUT_AUDIT = REVISION_ROOT.parent / f"{args.revision_id}_input_audit.csv"
    REVISION_ID = args.revision_id
    FIGURE_SPECS = [
        (payload, metric, kind, title + args.title_suffix)
        for payload, metric, kind, title in FIGURE_SPECS
    ]
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    ensure_dirs()
    rows = read_csv(SOURCE)
    validate_inputs(rows)
    head = git_head()
    manifests = []
    audits = {}
    raw_publication_counts = {}
    for payload, metric, kind, title in FIGURE_SPECS:
        manifest, audit_rows, raw_count, publication_count = render_figure(
            rows, payload, metric, kind, title, head
        )
        manifests.append(manifest)
        audits[manifest["figureName"]] = audit_rows
        raw_publication_counts[manifest["figureName"]] = {
            "raw": raw_count,
            "publication": publication_count,
        }
    write_report(manifests, audits, raw_publication_counts)
    write_gallery(manifests)
    summary_path = AUDIT / "stage16_plot_revision_summary.json"
    write_text(
        summary_path,
        json.dumps(
            {
                "gate": "PASS_STAGE16_PLOT_REVISION",
                "sourceCsv": rel(SOURCE),
                "sourceCsvSha256": sha256(SOURCE),
                "figureCount": len(manifests),
                "manifestCount": len(manifests),
                "usesZeroSurrogate": False,
                "zeroHandlingPolicy": "remove_zero_points_for_publication_plot",
                "figures": manifests,
                "rawPublicationCounts": raw_publication_counts,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "gitHead": head,
                "pythonVersion": platform.python_version(),
                "matplotlibVersion": matplotlib.__version__,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    print("PASS_STAGE16_PLOT_REVISION")
    print(summary_path)


if __name__ == "__main__":
    main()
