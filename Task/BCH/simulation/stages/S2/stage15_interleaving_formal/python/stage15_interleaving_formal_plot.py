import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
RESULTS = STAGE / "results"
DATA = RESULTS / "figure_data"
PLOTS = RESULTS / "plots"
MANIFESTS = RESULTS / "manifests"
STAGE_ID = "stage15_interleaving_formal"
METHOD = RESULTS / f"{STAGE_ID}_method_results.csv"
DEPTH = RESULTS / f"{STAGE_ID}_depth_results.csv"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]
STEMS = {
    "K200_S15": "k200_s15", "K200_M255K207": "k200_m255k207",
    "K200_M511K421": "k200_m511k421", "K200_M511K385": "k200_m511k385",
    "K300_S15": "k300_s15", "K300_M255K207": "k300_m255k207",
    "K300_M511K421": "k300_m511k421", "K300_M511K385": "k300_m511k385",
}


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def surrogate(row, metric):
    value = float(row[metric])
    if value > 0:
        return value, False
    denominator = (
        int(row["payloadBitsProcessed"]) if metric == "ber"
        else int(row["framesProcessed"])
    )
    return 0.5 / denominator, True


def publish(fig, figure_rows, plot_id, source, metadata):
    png = PLOTS / f"{plot_id}.png"
    data = DATA / f"{plot_id}_figure_data.csv"
    manifest = MANIFESTS / f"{plot_id}_plot_manifest.json"
    fig.tight_layout()
    fig.savefig(png, dpi=300, format="png")
    plt.close(fig)
    write(data, figure_rows)
    record = {
        "plotId": plot_id, "stageId": STAGE_ID,
        "gitCommit": metadata["gitCommit"],
        "sourceFiles": [source.name], "sourceSha256": [sha(source)],
        "figureDataFile": data.relative_to(STAGE).as_posix(),
        "figureDataSha256": sha(data),
        "pngFile": png.relative_to(STAGE).as_posix(),
        "pngSha256": sha(png),
        "xSourceColumn": metadata["xSourceColumn"],
        "xDisplayColumn": "xDisplay", "xDisplayLabel": metadata["xlabel"],
        "xPhysicalQuantity": metadata["xPhysicalQuantity"],
        "xUnit": metadata["xUnit"], "xTransformFormula": "identity",
        "ySourceColumn": metadata["ySourceColumn"], "yPlotColumn": "yPlot",
        "yDisplayLabel": metadata["ylabel"], "yUnit": metadata["yUnit"],
        "yScale": metadata["yScale"], "title": metadata["title"],
        "legendLabels": metadata["legendLabels"],
        "legendLocation": "upper right",
        "lineStyles": metadata["lineStyles"], "markers": metadata["markers"],
        "matplotlibVersion": matplotlib.__version__,
        "pythonVersion": platform.python_version(),
        "zeroHandling": (
            "Raw zero retained; logarithmic rate plots use "
            "0.5/denominator only in figure-data."
        ),
        "missingValueHandling": "NO_INTERPOLATION;MISSING_REMAINS_MISSING",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def line_plot(source_rows, source, case_id, metric, styles, kind):
    case = [row for row in source_rows if row["caseId"] == case_id]
    plot_id = (
        f"{STAGE_ID}_{STEMS[case_id]}_{metric}"
        if kind == "method"
        else f"{STAGE_ID}_{STEMS[case_id]}_depth_{metric}"
    )
    fig, axis = plt.subplots(figsize=(9.2, 5.8))
    figure_rows = []
    if kind == "method":
        series_keys = ["NONE", "BLOCK", "ROW_COLUMN", "PSEUDORANDOM"]
        labels = {
            mode: styles["interleaverStyles"][mode]["legend"]
            for mode in series_keys
        }
        style_for = {
            mode: (
                styles["interleaverStyles"][mode]["lineStyle"],
                styles["interleaverStyles"][mode]["marker"],
            ) for mode in series_keys
        }
        selector = lambda row, key: row["interleaverMode"] == key
    else:
        series_keys = [1, 4, 8, 16]
        labels = {1: "无交织", 4: "D=4", 8: "D=8", 16: "D=16"}
        style_for = {
            1: ("-", "o"), 4: ("--", "s"),
            8: ("-.", "^"), 16: (":", "D"),
        }
        selector = lambda row, key: int(row["interleaverDepth"]) == key
    for key in series_keys:
        group = [row for row in case if selector(row, key)]
        group.sort(key=lambda row: int(row["burstLengthBits"]))
        xs, ys = [], []
        for row in group:
            x = int(row["burstLengthBits"])
            y, zero = surrogate(row, metric)
            xs.append(x); ys.append(y)
            figure_rows.append({
                "plotId": plot_id, "caseId": case_id,
                "series": str(key), "legendLabel": labels[key],
                "xRaw": x, "xDisplay": x,
                "yRaw": row[metric], "yPlot": format(y, ".17g"),
                "yIsZero": str(zero).lower(),
                "framesProcessed": row["framesProcessed"],
                "payloadBitsProcessed": row["payloadBitsProcessed"],
                "plotSurrogateUsed": str(zero).lower(),
            })
        axis.plot(
            xs, ys, linestyle=style_for[key][0], marker=style_for[key][1],
            linewidth=1.7, markersize=4.5, label=labels[key],
        )
    display = "FER" if metric == "fer" else "BER"
    title = (
        styles["caseStyles"][case_id]["legend"]
        + ("交织方式" if kind == "method" else "交织深度")
        + display
    )
    axis.set_title(title);axis.set_xlabel("突发长度（bit）");axis.set_ylabel(display)
    axis.set_yscale("log");axis.grid(True,which="both",alpha=.28)
    axis.legend(loc="upper right")
    publish(fig, figure_rows, plot_id, source, {
        "gitCommit": case[0]["gitCommit"], "xSourceColumn": "burstLengthBits",
        "xlabel": "突发长度（bit）", "xPhysicalQuantity": "burst_length",
        "xUnit": "bit", "ySourceColumn": metric, "ylabel": display,
        "yUnit": "1", "yScale": "log", "title": title,
        "legendLabels": [labels[key] for key in series_keys],
        "lineStyles": {labels[k]: style_for[k][0] for k in series_keys},
        "markers": {labels[k]: style_for[k][1] for k in series_keys},
    })


def summary_bar(method, selection, styles, payload):
    cases = [case for case in CASES if case.startswith(f"K{payload}")]
    selection_map = {row["caseId"]: row for row in selection}
    values = [float(selection_map[case]["toleranceL1e1"]) for case in cases]
    labels = [styles["caseStyles"][case]["legend"] for case in cases]
    plot_id = f"{STAGE_ID}_k{payload}_tolerance_bar"
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.bar(labels, values, color=[
        styles["caseStyles"][case]["color"] for case in cases
    ])
    axis.set_title(f"{payload}比特BCH交织突发容限")
    axis.set_ylabel("突发容限（bit）");axis.grid(True,axis="y",alpha=.28)
    figure_rows = [{
        "plotId": plot_id, "caseId": case, "legendLabel": label,
        "xRaw": index, "xDisplay": index, "yRaw": value, "yPlot": value,
        "yIsZero": str(value == 0).lower(), "framesProcessed": 0,
        "payloadBitsProcessed": 0, "plotSurrogateUsed": "false",
    } for index,(case,label,value) in enumerate(zip(cases,labels,values))]
    publish(fig, figure_rows, plot_id, METHOD, {
        "gitCommit": method[0]["gitCommit"], "xSourceColumn": "caseId",
        "xlabel": "BCH方案", "xPhysicalQuantity": "case_category", "xUnit": "1",
        "ySourceColumn": "toleranceL1e1", "ylabel": "突发容限（bit）",
        "yUnit": "bit", "yScale": "linear",
        "title": f"{payload}比特BCH交织突发容限",
        "legendLabels": labels, "lineStyles": {}, "markers": {},
    })


def heatmap(method, styles, payload):
    subset = [
        row for row in method if int(row["payloadLength"]) == payload
        and row["interleaverMode"] != "NONE"
    ]
    lengths = sorted({int(row["burstLengthBits"]) for row in subset})
    modes = ["BLOCK", "ROW_COLUMN", "PSEUDORANDOM"]
    matrix = np.array([
        [
            np.mean([
                float(row["relativeFerReduction"])
                for row in subset if row["interleaverMode"] == mode
                and int(row["burstLengthBits"]) == length
                and row["relativeFerReduction"] != ""
            ]) if any(
                row["interleaverMode"] == mode
                and int(row["burstLengthBits"]) == length
                and row["relativeFerReduction"] != "" for row in subset
            ) else np.nan
            for length in lengths
        ] for mode in modes
    ])
    plot_id = f"{STAGE_ID}_k{payload}_fer_improvement_heatmap"
    fig, axis = plt.subplots(figsize=(10, 4.8))
    image = axis.imshow(matrix, aspect="auto", interpolation="none", cmap="viridis")
    axis.set_xticks(range(len(lengths)), lengths)
    axis.set_yticks(range(len(modes)), [
        styles["interleaverStyles"][mode]["legend"] for mode in modes
    ])
    axis.set_xlabel("突发长度（bit）");axis.set_title(f"{payload}比特BCH FER改善")
    fig.colorbar(image, ax=axis, label="相对FER降低")
    figure_rows = []
    for row_index, mode in enumerate(modes):
        for col_index, length in enumerate(lengths):
            value = matrix[row_index, col_index]
            figure_rows.append({
                "plotId": plot_id, "caseId": f"K{payload}_AGGREGATE",
                "series": mode,
                "legendLabel": styles["interleaverStyles"][mode]["legend"],
                "xRaw": length, "xDisplay": length,
                "yRaw": "" if np.isnan(value) else format(value, ".17g"),
                "yPlot": "" if np.isnan(value) else format(value, ".17g"),
                "yIsZero": "false", "framesProcessed": 0,
                "payloadBitsProcessed": 0, "plotSurrogateUsed": "false",
            })
    publish(fig, figure_rows, plot_id, METHOD, {
        "gitCommit": method[0]["gitCommit"], "xSourceColumn": "burstLengthBits",
        "xlabel": "突发长度（bit）", "xPhysicalQuantity": "burst_length",
        "xUnit": "bit", "ySourceColumn": "relativeFerReduction",
        "ylabel": "相对FER降低", "yUnit": "1", "yScale": "linear",
        "title": f"{payload}比特BCH FER改善",
        "legendLabels": [styles["interleaverStyles"][m]["legend"] for m in modes],
        "lineStyles": {}, "markers": {},
    })


def aggregate_plot(method, selection, styles, metric, suffix, title, ylabel):
    chosen = {row["caseId"]: row["bestInterleaverMode"] for row in selection}
    data = [
        row for row in method
        if row["interleaverMode"] == chosen[row["caseId"]]
    ]
    plot_id = f"{STAGE_ID}_{suffix}"
    fig, axis = plt.subplots(figsize=(10, 6))
    figure_rows = []
    for case in CASES:
        group = [row for row in data if row["caseId"] == case]
        group.sort(key=lambda row: int(row["burstLengthBits"]))
        xs = [int(row["burstLengthBits"]) for row in group]
        ys = [float(row[metric]) for row in group]
        axis.plot(xs, ys, color=styles["caseStyles"][case]["color"],
                  marker="o", linewidth=1.5,
                  label=styles["caseStyles"][case]["legend"])
        for row,x,y in zip(group,xs,ys):
            figure_rows.append({
                "plotId": plot_id, "caseId": case,
                "series": chosen[case],
                "legendLabel": styles["caseStyles"][case]["legend"],
                "xRaw": x, "xDisplay": x, "yRaw": y, "yPlot": y,
                "yIsZero": str(y == 0).lower(),
                "framesProcessed": row["framesProcessed"],
                "payloadBitsProcessed": row["payloadBitsProcessed"],
                "plotSurrogateUsed": "false",
            })
    axis.set_title(title);axis.set_xlabel("突发长度（bit）");axis.set_ylabel(ylabel)
    axis.grid(True,alpha=.28);axis.legend(loc="upper right",ncol=2)
    publish(fig, figure_rows, plot_id, METHOD, {
        "gitCommit": method[0]["gitCommit"], "xSourceColumn": "burstLengthBits",
        "xlabel": "突发长度（bit）", "xPhysicalQuantity": "burst_length",
        "xUnit": "bit", "ySourceColumn": metric, "ylabel": ylabel,
        "yUnit": "block" if "Affected" in metric else "ns",
        "yScale": "linear", "title": title,
        "legendLabels": [styles["caseStyles"][c]["legend"] for c in CASES],
        "lineStyles": {}, "markers": {},
    })


def main():
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False
    DATA.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    method = rows(METHOD);depth = rows(DEPTH)
    selection = rows(RESULTS / f"{STAGE_ID}_best_interleaver_selection.csv")
    styles = json.loads(
        (STAGE13 / "configs/stage13_burst_interleaving_validation_plot_style.json")
        .read_text(encoding="utf-8")
    )
    for case in CASES:
        line_plot(method, METHOD, case, "fer", styles, "method")
        line_plot(method, METHOD, case, "ber", styles, "method")
        line_plot(depth, DEPTH, case, "fer", styles, "depth")
    for payload in (200, 300):
        summary_bar(method, selection, styles, payload)
        heatmap(method, styles, payload)
    aggregate_plot(
        method, selection, styles, "meanAffectedCodeBlocks",
        "error_spreading", "BCH交织错误扩散", "受影响码块数",
    )
    aggregate_plot(
        method, selection, styles, "interleaverTimeMeanNs",
        "latency_overhead", "BCH交织时延开销", "交织时延（ns）",
    )
    print("PASS_STAGE15_INTERLEAVING_FORMAL_PLOT")


if __name__ == "__main__":
    main()
