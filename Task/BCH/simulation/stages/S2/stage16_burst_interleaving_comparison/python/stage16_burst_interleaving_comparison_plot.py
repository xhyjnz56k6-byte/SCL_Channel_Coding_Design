import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
RESULTS = STAGE / "results"
DATA = RESULTS / "figure_data"
PLOTS = RESULTS / "plots"
MANIFESTS = RESULTS / "manifests"
STAGE_ID = "stage16_burst_interleaving_comparison"
SOURCE = RESULTS / f"{STAGE_ID}_raw_results.csv"
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
CONFIGS = ["NONE_L0", "NONE_LREP", "BEST_LREP"]
CONFIG_LABELS = {
    "NONE_L0": "无突发",
    "NONE_LREP": "无交织突发",
    "BEST_LREP": "最佳交织突发",
}
CONFIG_STYLES = {
    "NONE_L0": ("-", "o"),
    "NONE_LREP": ("--", "s"),
    "BEST_LREP": ("-.", "^"),
}


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(fig, rows, plot_id, metadata):
    png = PLOTS / f"{plot_id}.png"
    data = DATA / f"{plot_id}_figure_data.csv"
    manifest_path = MANIFESTS / f"{plot_id}_plot_manifest.json"
    fig.tight_layout()
    fig.savefig(png, dpi=300, format="png")
    plt.close(fig)
    write(data, rows)
    manifest = {
        "plotId": plot_id,
        "stageId": STAGE_ID,
        "gitCommit": metadata["gitCommit"],
        "sourceFiles": [SOURCE.name],
        "sourceSha256": [sha(SOURCE)],
        "figureDataFile": data.relative_to(STAGE).as_posix(),
        "figureDataSha256": sha(data),
        "pngFile": png.relative_to(STAGE).as_posix(),
        "pngSha256": sha(png),
        "xSourceColumn": "targetSnrDb",
        "xDisplayColumn": "xDisplay",
        "xDisplayLabel": "SNR",
        "xPhysicalQuantity": "waveform_snr",
        "xUnit": "dB",
        "xTransformFormula": "identity",
        "ySourceColumn": metadata["metric"],
        "yPlotColumn": "yPlot",
        "yDisplayLabel": metadata["metric"].upper(),
        "yUnit": "1",
        "yScale": "log",
        "title": metadata["title"],
        "legendLabels": metadata["legendLabels"],
        "legendLocation": "upper right",
        "lineStyles": metadata["lineStyles"],
        "markers": metadata["markers"],
        "matplotlibVersion": matplotlib.__version__,
        "pythonVersion": platform.python_version(),
        "zeroHandling": (
            "Raw zero retained; figure-data uses 0.5/denominator "
            "only for logarithmic display."
        ),
        "missingValueHandling": "NO_INTERPOLATION;MISSING_REMAINS_MISSING",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def figure_row(plot_id, row, metric, legend):
    raw = float(row[metric])
    denominator = (
        int(row["payloadBitsProcessed"])
        if metric == "ber" else int(row["framesProcessed"])
    )
    plotted = raw if raw > 0 else 0.5 / denominator
    return {
        "plotId": plot_id,
        "caseId": row["caseId"],
        "configurationId": row["configurationId"],
        "legendLabel": legend,
        "xRaw": row["targetSnrDb"],
        "xDisplay": row["targetSnrDb"],
        "derivedEbN0Db": row["derivedEbN0Db"],
        "actualRate": row["actualRate"],
        "yRaw": row[metric],
        "yPlot": format(plotted, ".17g"),
        "yIsZero": str(raw == 0).lower(),
        "framesProcessed": row["framesProcessed"],
        "payloadBitsProcessed": row["payloadBitsProcessed"],
        "plotSurrogateUsed": str(raw == 0).lower(),
    }


def case_plot(rows, case_id, metric, styles):
    subset = [row for row in rows if row["caseId"] == case_id]
    plot_id = f"{STAGE_ID}_{STEMS[case_id]}_{metric}_vs_snr"
    fig, axis = plt.subplots(figsize=(9.2, 5.8))
    figure_rows = []
    color = styles["caseStyles"][case_id]["color"]
    for configuration in CONFIGS:
        group = [
            row for row in subset if row["configurationId"] == configuration
        ]
        group.sort(key=lambda row: int(row["snrIndex"]))
        plotted = [
            float(figure_row(plot_id, row, metric, CONFIG_LABELS[configuration])["yPlot"])
            for row in group
        ]
        figure_rows.extend(
            figure_row(plot_id, row, metric, CONFIG_LABELS[configuration])
            for row in group
        )
        line, marker = CONFIG_STYLES[configuration]
        axis.plot(
            [float(row["targetSnrDb"]) for row in group], plotted,
            color=color, linestyle=line, marker=marker, markevery=2,
            linewidth=1.7, markersize=4.2, label=CONFIG_LABELS[configuration],
        )
    title = styles["caseStyles"][case_id]["legend"] + "突发信道适应性"
    axis.set_title(title)
    axis.set_xlabel("SNR")
    axis.set_ylabel(metric.upper())
    axis.set_yscale("log")
    axis.grid(True, which="both", alpha=0.28)
    axis.legend(loc="upper right")
    publish(fig, figure_rows, plot_id, {
        "gitCommit": subset[0]["gitCommit"],
        "metric": metric,
        "title": title,
        "legendLabels": [CONFIG_LABELS[c] for c in CONFIGS],
        "lineStyles": {CONFIG_LABELS[c]: CONFIG_STYLES[c][0] for c in CONFIGS},
        "markers": {CONFIG_LABELS[c]: CONFIG_STYLES[c][1] for c in CONFIGS},
    })


def aggregate_plot(rows, payload, metric, styles):
    cases = [case for case in CASES if case.startswith(f"K{payload}")]
    plot_id = f"{STAGE_ID}_k{payload}_{metric}_vs_snr"
    fig, axis = plt.subplots(figsize=(11.2, 7.0))
    figure_rows = []
    legends = []
    lines = {}
    markers = {}
    for case_id in cases:
        short_case = styles["caseStyles"][case_id]["legend"].replace(
            str(payload), ""
        )
        for configuration in CONFIGS:
            group = [
                row for row in rows
                if row["caseId"] == case_id
                and row["configurationId"] == configuration
            ]
            group.sort(key=lambda row: int(row["snrIndex"]))
            legend = f"{short_case}-{CONFIG_LABELS[configuration]}"
            line, marker = CONFIG_STYLES[configuration]
            values = [
                figure_row(plot_id, row, metric, legend) for row in group
            ]
            figure_rows.extend(values)
            axis.plot(
                [float(row["targetSnrDb"]) for row in group],
                [float(value["yPlot"]) for value in values],
                color=styles["caseStyles"][case_id]["color"],
                linestyle=line, marker=marker, markevery=4,
                linewidth=1.25, markersize=3.4, label=legend,
            )
            legends.append(legend)
            lines[legend] = line
            markers[legend] = marker
    title = f"{payload}比特BCH突发信道适应性"
    axis.set_title(title)
    axis.set_xlabel("SNR")
    axis.set_ylabel(metric.upper())
    axis.set_yscale("log")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(loc="upper right", fontsize=7.5, ncol=2)
    publish(fig, figure_rows, plot_id, {
        "gitCommit": rows[0]["gitCommit"],
        "metric": metric,
        "title": title,
        "legendLabels": legends,
        "lineStyles": lines,
        "markers": markers,
    })


def main():
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False
    DATA.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    rows = read(SOURCE)
    styles = json.loads(
        (
            STAGE13
            / "configs/stage13_burst_interleaving_validation_plot_style.json"
        ).read_text(encoding="utf-8")
    )
    for case_id in CASES:
        for metric in ("fer", "ber"):
            case_plot(rows, case_id, metric, styles)
    for payload in (200, 300):
        for metric in ("fer", "ber"):
            aggregate_plot(rows, payload, metric, styles)
    print("PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_PLOT")


if __name__ == "__main__":
    main()
