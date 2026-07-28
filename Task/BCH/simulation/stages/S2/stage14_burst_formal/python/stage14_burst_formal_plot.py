import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
FIGURE_DATA = RESULTS / "figure_data"
PLOTS = RESULTS / "plots"
MANIFESTS = RESULTS / "manifests"
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
STAGE_ID = "stage14_burst_formal"
SOURCE = RESULTS / f"{STAGE_ID}_raw_results.csv"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def configure_fonts():
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
        "Arial Unicode MS", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def plot_value(row, metric):
    raw = float(row[metric])
    if metric == "ber":
        denominator = int(row["payloadBitsProcessed"])
        surrogate = 0.5 / denominator
    elif metric in {
        "fer", "miscorrectionRate", "decoderFailureRate",
        "undetectedErrorRate",
    }:
        denominator = int(row["framesProcessed"])
        surrogate = 0.5 / denominator
    else:
        return raw, False, False
    if raw == 0.0:
        return surrogate, True, True
    return raw, False, False


def create_figure(rows, styles, spec):
    plot_id = f"{STAGE_ID}_{spec['suffix']}"
    png_path = PLOTS / f"{plot_id}.png"
    data_path = FIGURE_DATA / f"{plot_id}_figure_data.csv"
    manifest_path = MANIFESTS / f"{plot_id}_plot_manifest.json"
    selected = [
        row for row in rows
        if spec.get("payload") is None
        or int(row["payloadLength"]) == spec["payload"]
    ]
    case_order = list(styles["caseStyles"])
    figure_rows = []
    fig, axis = plt.subplots(figsize=(10.0, 6.2))
    for case_id in case_order:
        series = [row for row in selected if row["caseId"] == case_id]
        if not series:
            continue
        series.sort(key=lambda row: int(row["burstLengthBits"]))
        x_values = []
        y_values = []
        for row in series:
            if spec["x"] == "burstRatio":
                x_raw = float(row["burstRatio"])
                x_display = 100.0 * x_raw
            else:
                x_raw = float(row["burstLengthBits"])
                x_display = x_raw
            if spec["metric"] == "decoderTimeMeanUs":
                y_raw = float(row["decoderTimeMeanNs"])
                y_plot = y_raw / 1000.0
                y_zero = False
                surrogate_used = False
            else:
                y_raw = float(row[spec["metric"]])
                y_plot, y_zero, surrogate_used = plot_value(
                    row, spec["metric"]
                )
            x_values.append(x_display)
            y_values.append(y_plot)
            figure_rows.append({
                "plotId": plot_id,
                "caseId": case_id,
                "legendLabel": styles["caseStyles"][case_id]["legend"],
                "xSourceColumn": spec["x"],
                "xRaw": format(x_raw, ".17g"),
                "xDisplay": format(x_display, ".17g"),
                "ySourceColumn": spec["metric"],
                "yRaw": format(y_raw, ".17g"),
                "yPlot": format(y_plot, ".17g"),
                "yIsZero": str(y_zero).lower(),
                "ferRaw": row["fer"],
                "ferPlot": format(
                    plot_value(row, "fer")[0], ".17g"
                ),
                "ferIsZero": str(float(row["fer"]) == 0.0).lower(),
                "berRaw": row["ber"],
                "berPlot": format(
                    plot_value(row, "ber")[0], ".17g"
                ),
                "berIsZero": str(float(row["ber"]) == 0.0).lower(),
                "plotSurrogateUsed": str(surrogate_used).lower(),
                "framesProcessed": row["framesProcessed"],
                "payloadBitsProcessed": row["payloadBitsProcessed"],
            })
        style = styles["caseStyles"][case_id]
        none_style = styles["interleaverStyles"]["NONE"]
        axis.plot(
            x_values,
            y_values,
            color=style["color"],
            linestyle=none_style["lineStyle"],
            marker=none_style["marker"],
            linewidth=1.8,
            markersize=4.5,
            label=style["legend"],
        )
    axis.set_title(spec["title"])
    axis.set_xlabel(spec["xlabel"])
    axis.set_ylabel(spec["ylabel"])
    if spec["scale"] == "log":
        axis.set_yscale("log")
    axis.grid(True, which="both", alpha=0.28)
    legend = axis.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(png_path, dpi=300, format="png")
    plt.close(fig)
    write_rows(data_path, figure_rows)
    source_sha = sha256(SOURCE)
    manifest = {
        "plotId": plot_id,
        "stageId": STAGE_ID,
        "gitCommit": rows[0]["gitCommit"],
        "sourceFiles": [SOURCE.name],
        "sourceSha256": [source_sha],
        "figureDataFile": data_path.relative_to(STAGE).as_posix(),
        "figureDataSha256": sha256(data_path),
        "pngFile": png_path.relative_to(STAGE).as_posix(),
        "pngSha256": sha256(png_path),
        "xSourceColumn": spec["x"],
        "xDisplayColumn": "xDisplay",
        "xDisplayLabel": spec["xlabel"],
        "xPhysicalQuantity": spec["xPhysicalQuantity"],
        "xUnit": spec["xUnit"],
        "xTransformFormula": spec["xTransform"],
        "ySourceColumn": spec["metric"],
        "yPlotColumn": "yPlot",
        "yDisplayLabel": spec["ylabel"],
        "yUnit": spec["yUnit"],
        "yScale": spec["scale"],
        "title": spec["title"],
        "legendLabels": [
            text.get_text() for text in legend.get_texts()
        ],
        "legendLocation": "upper right",
        "lineStyles": {
            case_id: styles["interleaverStyles"]["NONE"]["lineStyle"]
            for case_id in case_order
            if any(row["caseId"] == case_id for row in selected)
        },
        "markers": {
            case_id: styles["interleaverStyles"]["NONE"]["marker"]
            for case_id in case_order
            if any(row["caseId"] == case_id for row in selected)
        },
        "matplotlibVersion": matplotlib.__version__,
        "pythonVersion": platform.python_version(),
        "zeroHandling": (
            "Raw zero retained; plot uses 0.5/denominator only in "
            "figure-data for logarithmic display."
        ),
        "missingValueHandling": "NO_INTERPOLATION",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    configure_fonts()
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    rows = read_rows(SOURCE)
    styles = json.loads(
        (
            STAGE13
            / "configs/stage13_burst_interleaving_validation_plot_style.json"
        ).read_text(encoding="utf-8")
    )
    specs = []
    for payload in (200, 300):
        prefix = f"k{payload}"
        title_prefix = f"{payload}比特BCH"
        specs.extend([
            {
                "suffix": f"{prefix}_ber_vs_burst_length",
                "payload": payload, "x": "burstLengthBits",
                "metric": "ber", "title": title_prefix + "误比特率对比",
                "xlabel": "突发长度（bit）", "ylabel": "BER",
                "scale": "log", "xPhysicalQuantity": "burst_length",
                "xUnit": "bit", "xTransform": "identity", "yUnit": "1",
            },
            {
                "suffix": f"{prefix}_fer_vs_burst_length",
                "payload": payload, "x": "burstLengthBits",
                "metric": "fer", "title": title_prefix + "误帧率对比",
                "xlabel": "突发长度（bit）", "ylabel": "FER",
                "scale": "log", "xPhysicalQuantity": "burst_length",
                "xUnit": "bit", "xTransform": "identity", "yUnit": "1",
            },
            {
                "suffix": f"{prefix}_miscorrection_vs_burst_length",
                "payload": payload, "x": "burstLengthBits",
                "metric": "miscorrectionRate",
                "title": title_prefix + "误纠率对比",
                "xlabel": "突发长度（bit）", "ylabel": "误纠率",
                "scale": "log", "xPhysicalQuantity": "burst_length",
                "xUnit": "bit", "xTransform": "identity", "yUnit": "1",
            },
            {
                "suffix": f"{prefix}_failure_vs_burst_length",
                "payload": payload, "x": "burstLengthBits",
                "metric": "decoderFailureRate",
                "title": title_prefix + "译码失败率对比",
                "xlabel": "突发长度（bit）", "ylabel": "译码失败率",
                "scale": "log", "xPhysicalQuantity": "burst_length",
                "xUnit": "bit", "xTransform": "identity", "yUnit": "1",
            },
            {
                "suffix": f"{prefix}_fer_vs_burst_ratio",
                "payload": payload, "x": "burstRatio",
                "metric": "fer", "title": title_prefix + "归一化突发误帧率",
                "xlabel": "突发比例（%）", "ylabel": "FER",
                "scale": "log", "xPhysicalQuantity": "burst_ratio",
                "xUnit": "%", "xTransform": "100*burstRatio", "yUnit": "1",
            },
        ])
    specs.extend([
        {
            "suffix": "affected_blocks_vs_burst_length",
            "payload": None, "x": "burstLengthBits",
            "metric": "meanAffectedCodeBlocks",
            "title": "BCH受影响码块数对比",
            "xlabel": "突发长度（bit）", "ylabel": "受影响码块数",
            "scale": "linear", "xPhysicalQuantity": "burst_length",
            "xUnit": "bit", "xTransform": "identity", "yUnit": "block",
        },
        {
            "suffix": "max_errors_per_block_vs_burst_length",
            "payload": None, "x": "burstLengthBits",
            "metric": "meanMaxErrorsInOneCodeBlock",
            "title": "BCH单码块错误集中度",
            "xlabel": "突发长度（bit）", "ylabel": "单码块最大错误数",
            "scale": "linear", "xPhysicalQuantity": "burst_length",
            "xUnit": "bit", "xTransform": "identity", "yUnit": "bit",
        },
        {
            "suffix": "latency_vs_burst_length",
            "payload": None, "x": "burstLengthBits",
            "metric": "decoderTimeMeanUs",
            "title": "BCH译码时延对比",
            "xlabel": "突发长度（bit）", "ylabel": "译码时延（μs）",
            "scale": "linear", "xPhysicalQuantity": "burst_length",
            "xUnit": "bit", "xTransform": "identity", "yUnit": "us",
        },
    ])
    for spec in specs:
        create_figure(rows, styles, spec)
    print("PASS_STAGE14_BURST_FORMAL_PLOT")


if __name__ == "__main__":
    main()

