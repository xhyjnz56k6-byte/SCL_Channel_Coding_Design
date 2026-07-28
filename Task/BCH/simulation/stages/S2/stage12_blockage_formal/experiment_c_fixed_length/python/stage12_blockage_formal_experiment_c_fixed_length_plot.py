import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

EXPERIMENT = Path(__file__).resolve().parents[1]
RESULTS = EXPERIMENT / "results"
PLOTS = EXPERIMENT / "plots"
MANIFESTS = EXPERIMENT / "manifests"
PLOTS.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)
SOURCE = RESULTS / "stage12_blockage_formal_experiment_c_fixed_length_result_summary.csv"

with SOURCE.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

STYLES = {
    "S15": ("分块", "#0072B2", "-", "o"),
    "M255K207": ("255整块", "#D55E00", "--", "s"),
    "M511K421": ("421整块", "#009E73", "-.", "^"),
    "M511K385": ("385整块", "#CC79A7", ":", "D"),
}


def curve_style(case_id, payload_length):
    key = case_id.split("_", 1)[1]
    label, color, line, marker = STYLES[key]
    if payload_length == 300 and key == "M255K207":
        label = "255双块"
    return label, color, line, marker


for payload in (200, 300):
    for metric, title, y_label in [
        ("ber", "误码率", "BER"),
        ("fer", "误帧率", "FER"),
        ("miscorrectionRate", "误纠率", "误纠率"),
    ]:
        figure_rows = []
        plt.figure(figsize=(7.2, 4.8))
        case_ids = sorted({r["caseId"] for r in rows if int(r["payloadLength"]) == payload})
        for case_id in case_ids:
            group = [r for r in rows if r["caseId"] == case_id]
            group.sort(key=lambda r: int(r["requestedBlockageLengthSymbols"]))
            label, color, line, marker = curve_style(case_id, payload)
            x_values = [int(r["requestedBlockageLengthSymbols"]) for r in group]
            raw_values = [float(r[metric]) for r in group]
            plot_values = [
                value if value > 0 else 0.5 / (
                    int(row["totalPayloadBits"]) if metric == "ber" else int(row["totalFrames"])
                )
                for value, row in zip(raw_values, group)
            ]
            plt.plot(
                x_values, plot_values, label=label, color=color,
                linestyle=line, marker=marker,
            )
            for row, raw_value, plot_value in zip(group, raw_values, plot_values):
                figure_rows.append({
                    "caseId": case_id,
                    "legendLabel": label,
                    "payloadLength": payload,
                    "encodedLength": row["encodedLength"],
                    "actualRate": row["actualRate"],
                    "ebn0Db": row["ebn0Db"],
                    "snrDb": row["snrDb"],
                    "requestedBlockageLengthSymbols": row["requestedBlockageLengthSymbols"],
                    "blockageLengthSymbols": row["blockageLengthSymbols"],
                    "actualBlockageRatio": row["actualBlockageRatio"],
                    "metricName": metric,
                    "metricValue": raw_value,
                    "totalFrames": row["totalFrames"],
                    "errorCount": (
                        row["payloadErrorBits"] if metric == "ber"
                        else row["payloadErrorFrames"] if metric == "fer"
                        else row["miscorrectionFrames"]
                    ),
                    "isZeroObserved": int(raw_value == 0),
                    "plotSurrogateUsed": int(raw_value == 0),
                    "plotValue": plot_value,
                })
        plt.xlabel("遮挡长度")
        plt.ylabel(y_label)
        plt.title(f"{payload}比特BCH固定长度遮挡{title}")
        plt.yscale("log")
        plt.xticks([5, 10, 20, 30])
        plt.grid(True, which="both", alpha=0.3)
        plt.legend(loc="upper left")
        plt.tight_layout()
        metric_stem = "miscorrection" if metric == "miscorrectionRate" else metric
        stem = f"stage12_blockage_formal_experiment_c_fixed_length_k{payload}_{metric_stem}_vs_length"
        png = PLOTS / f"{stem}.png"
        data = RESULTS / f"{stem}_figure_data.csv"
        plt.savefig(png, dpi=300)
        plt.close()
        with data.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=figure_rows[0].keys())
            writer.writeheader()
            writer.writerows(figure_rows)
        manifest = {
            "stageId": "stage12_blockage_formal",
            "experimentId": "experiment_c_fixed_length",
            "sourceCsv": str(SOURCE.relative_to(EXPERIMENT)),
            "sourceCsvSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "figureData": str(data.relative_to(EXPERIMENT)),
            "figureDataSha256": hashlib.sha256(data.read_bytes()).hexdigest(),
            "png": str(png.relative_to(EXPERIMENT)),
            "pngSha256": hashlib.sha256(png.read_bytes()).hexdigest(),
            "xAxis": "遮挡长度",
            "snrFormula": "snrDb=ebn0Db+10*log10(actualRate)",
            "zeroValuePolicy": "raw zero retained; plotValue=0.5/denominator only",
        }
        (MANIFESTS / f"{stem}_plot_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

print("PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_C_FIXED_LENGTH_PLOT")
