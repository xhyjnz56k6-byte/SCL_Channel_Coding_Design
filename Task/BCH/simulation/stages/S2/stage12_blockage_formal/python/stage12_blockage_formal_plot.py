import csv
import hashlib
import json
from pathlib import Path
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
PLOTS = STAGE / "plots"
MANIFESTS = STAGE / "manifests"
PLOTS.mkdir(exist_ok=True)
MANIFESTS.mkdir(exist_ok=True)
SOURCE = RESULTS / "stage12_blockage_formal_result_summary.csv"
with SOURCE.open(encoding="utf-8", newline="") as stream:
    rows = [row for row in csv.DictReader(stream) if row["experimentType"] == "SNR"]

styles = {
    "K200_S15": ("分块", "#0072B2", "-", "o"),
    "K200_M255K207": ("255整块", "#D55E00", "--", "s"),
    "K200_M511K421": ("421整块", "#009E73", "-.", "^"),
    "K200_M511K385": ("385整块", "#CC79A7", ":", "D"),
    "K300_S15": ("分块", "#0072B2", "-", "o"),
    "K300_M255K207": ("255双块", "#D55E00", "--", "s"),
    "K300_M511K421": ("421整块", "#009E73", "-.", "^"),
    "K300_M511K385": ("385整块", "#CC79A7", ":", "D"),
}

for payload in (200, 300):
    for metric, ylabel in (("ber", "BER"), ("fer", "FER")):
        figure_rows = []
        plt.figure(figsize=(7.2, 4.8))
        for case in [case for case in styles if case.startswith(f"K{payload}")]:
            group = sorted((row for row in rows if row["caseId"] == case),
                           key=lambda row: float(row["snrDb"]))
            label, color, line, marker = styles[case]
            raw = [float(row[metric]) for row in group]
            plot = [value if value > 0 else 0.5 / (int(row["totalPayloadBits"]) if metric == "ber" else int(row["totalFrames"]))
                    for value, row in zip(raw, group)]
            x = [float(row["snrDb"]) for row in group]
            plt.plot(x, plot, label=label, color=color, linestyle=line, marker=marker, linewidth=1.5)
            for row, value, plotted in zip(group, raw, plot):
                figure_rows.append({
                    "caseId": case, "legendLabel": label, "payloadLength": payload,
                    "encodedLength": row["encodedLength"], "actualRate": row["actualRate"],
                    "ebn0Db": row["ebn0Db"], "targetSnrDb": row["snrDb"], "snrDb": row["snrDb"],
                    "metricName": metric, "metricValue": f"{value:.17g}",
                    "totalFrames": row["totalFrames"],
                    "errorCount": row["payloadErrorBits"] if metric == "ber" else row["payloadErrorFrames"],
                    "isZeroObserved": int(value == 0), "plotSurrogateUsed": int(value == 0),
                    "plotValue": f"{plotted:.17g}",
                })
        plt.xlabel("SNR")
        plt.ylabel(ylabel)
        plt.title(f"{payload}比特BCH短时遮挡{ylabel}对比")
        plt.xlim(0.0, 8.0)
        plt.xticks([0.5 * i for i in range(17)])
        plt.yscale("log")
        plt.grid(True, which="both", alpha=.3)
        plt.legend(loc="upper right")
        plt.tight_layout()
        stem = f"stage12_blockage_formal_k{payload}_{metric}_vs_snr"
        png = PLOTS / f"{stem}.png"
        figure_data = RESULTS / f"stage12_blockage_formal_figure_data_k{payload}_{metric}_vs_snr.csv"
        plt.savefig(png, dpi=300)
        plt.close()
        with figure_data.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=figure_rows[0].keys())
            writer.writeheader()
            writer.writerows(figure_rows)
        manifest = {
            "stageId": "stage12_blockage_formal", "experiment": "B_dense_snr",
            "targetSnrGridDb": [0.5 * i for i in range(17)], "snrStepDb": 0.5,
            "snrMinDb": 0.0, "snrMaxDb": 8.0, "pointCountPerCase": 17,
            "xTransformFormula": "targetSnrDb=snrDb",
            "ebn0InverseFormula": "ebn0Db=targetSnrDb-10*log10(actualRate)",
            "stopRule": {"minFrames": 1000, "targetFrameErrors": 200, "maxFrames": 50000},
            "sourceCsv": str(SOURCE.relative_to(STAGE)),
            "sourceCsvSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "figureData": str(figure_data.relative_to(STAGE)),
            "figureDataSha256": hashlib.sha256(figure_data.read_bytes()).hexdigest(),
            "png": str(png.relative_to(STAGE)),
            "pngSha256": hashlib.sha256(png.read_bytes()).hexdigest(),
            "zeroValuePolicy": "raw zero retained; plotValue=0.5/denominator for log display only",
            "generatedFromGitCommit": rows[0]["gitCommit"],
            "caseIdToStyle": {case: {"legendLabel": styles[case][0], "color": styles[case][1],
                                      "lineStyle": styles[case][2], "marker": styles[case][3]} for case in styles if case.startswith(f"K{payload}")},
        }
        (MANIFESTS / f"stage12_blockage_formal_plot_manifest_k{payload}_{metric}_vs_snr.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("PASS_STAGE12_BLOCKAGE_FORMAL_DENSE_SNR_PLOT")
