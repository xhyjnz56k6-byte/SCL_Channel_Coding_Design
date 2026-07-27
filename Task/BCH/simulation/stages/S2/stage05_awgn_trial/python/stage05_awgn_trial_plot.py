import csv
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
PLOTS = STAGE / "plots"
SOURCE = RESULTS / "stage05_awgn_trial_results.csv"
STYLE = {
    "STYLE_1": ("#1f77b4", "-", "o"),
    "STYLE_2": ("#ff7f0e", "--", "s"),
    "STYLE_3": ("#2ca02c", "-.", "^"),
    "STYLE_4": ("#d62728", ":", "D"),
}


def sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_rows():
    with SOURCE.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    raw = read_rows()
    figure_rows = []
    manifests = []
    for payload, payload_tag in ((200, "k200"), (300, "k300")):
        selected = [row for row in raw if int(row["payloadLength"]) == payload]
        for metric, title_metric in (("ber", "误码率"), ("fer", "误帧率")):
            figure_id = f"stage05_awgn_trial_{payload_tag}_{metric}"
            data_rows = []
            for row in selected:
                denominator = int(row["totalPayloadBits"] if metric == "ber" else row["totalFrames"])
                raw_y = float(row[metric])
                zero_substituted = raw_y == 0.0
                plot_y = 0.5 / denominator if zero_substituted else raw_y
                data_rows.append({
                    "figureId": figure_id,
                    "caseId": row["caseId"],
                    "legendLabel": row["legendLabel"],
                    "styleId": row["styleId"],
                    "metric": metric.upper(),
                    "ebn0Index": row["ebn0Index"],
                    "ebn0Db": row["ebn0Db"],
                    "actualRate": row["actualRate"],
                    "snrLinear": row["snrLinear"],
                    "snrDb": row["snrDb"],
                    "rawY": format(raw_y, ".17g"),
                    "plotY": format(plot_y, ".17g"),
                    "denominator": denominator,
                    "zeroSurrogateApplied": str(zero_substituted).lower(),
                    "zeroSurrogateRule": "0.5/denominator",
                })
            data_rows.sort(key=lambda row: (row["caseId"], int(row["ebn0Index"])))
            data_path = PLOTS / f"{figure_id}_figure_data.csv"
            write_csv(data_path, data_rows)
            figure_rows.extend(data_rows)

            fig, axis = plt.subplots(figsize=(7.2, 5.2))
            for case_id in dict.fromkeys(row["caseId"] for row in data_rows):
                points = [row for row in data_rows if row["caseId"] == case_id]
                color, line, marker = STYLE[points[0]["styleId"]]
                axis.plot([float(row["snrDb"]) for row in points],
                          [float(row["plotY"]) for row in points],
                          color=color, linestyle=line, marker=marker, linewidth=1.5,
                          markersize=5, label=points[0]["legendLabel"])
            axis.set_xlabel("SNR (dB)")
            axis.set_ylabel(metric.upper())
            axis.set_title(f"{payload}比特BCH试运行{title_metric}")
            axis.set_yscale("log")
            axis.grid(True, which="both", linestyle=":", linewidth=0.6)
            axis.legend(loc="upper right")
            fig.tight_layout()
            png_path = PLOTS / f"{figure_id}.png"
            fig.savefig(png_path, dpi=300, format="png")
            plt.close(fig)
            manifests.append({
                "figureId": figure_id,
                "png": png_path.name,
                "figureData": data_path.name,
                "payloadLength": payload,
                "metric": metric.upper(),
                "title": f"{payload}比特BCH试运行{title_metric}",
                "xAxis": "SNR (dB)",
                "yScale": "log",
                "dpi": 300,
                "pngSha256": sha256(png_path),
                "figureDataSha256": sha256(data_path),
            })

    aggregate = PLOTS / "stage05_awgn_trial_figure_data.csv"
    write_csv(aggregate, figure_rows)
    manifest = {
        "stageId": "stage05_awgn_trial",
        "sourceResults": SOURCE.name,
        "sourceResultsSha256": sha256(SOURCE),
        "plotScriptSha256": sha256(Path(__file__)),
        "pythonVersion": platform.python_version(),
        "matplotlibVersion": matplotlib.__version__,
        "zeroSurrogateRule": "raw zero is plotted as 0.5/denominator; rawY remains zero",
        "aggregateFigureData": aggregate.name,
        "aggregateFigureDataSha256": sha256(aggregate),
        "figures": manifests,
    }
    (PLOTS / "stage05_awgn_trial_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_STAGE05_AWGN_TRIAL_PLOT")


if __name__ == "__main__":
    main()
