import csv
import hashlib
import json
import math
import platform
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
PLOTS = STAGE / "plots"
SOURCE = RESULTS / "stage07_awgn_dense_formal_results.csv"
CONFIG = STAGE / "configs/stage07_awgn_dense_formal_config.json"
ZERO_OBSERVED_UPPER_BOUND_FACTOR = 3.0
STYLE = {
    "STYLE_1": ("#1f77b4", "-", "o"),
    "STYLE_2": ("#ff7f0e", "--", "s"),
    "STYLE_3": ("#2ca02c", "-.", "^"),
    "STYLE_4": ("#d62728", ":", "D"),
}
FIGURES = [
    (200, "k200", "ber", "200比特BCH误码率对比", "BER", "log"),
    (200, "k200", "fer", "200比特BCH误帧率对比", "FER", "log"),
    (200, "k200", "decodeTimeMeanNs", "200比特BCH译码时延对比", "译码时延 (us)", "linear"),
    (300, "k300", "ber", "300比特BCH误码率对比", "BER", "log"),
    (300, "k300", "fer", "300比特BCH误帧率对比", "FER", "log"),
    (300, "k300", "decodeTimeMeanNs", "300比特BCH译码时延对比", "译码时延 (us)", "linear"),
]
FIGURE_FIELDS = [
    "figureId", "sourceCsv", "sourceRowId", "sourceRowSha256", "caseId", "payloadLength",
    "legendLabel", "styleId", "snrIndex", "snrDb", "snrLinear", "ebn0Db", "actualRate",
    "encodedLength", "metric", "rawNumerator", "rawDenominator", "rawY", "plotY",
    "isZeroObserved", "zeroObservedStatus", "plotSurrogateUsed", "plotSurrogateFormula",
    "oneSided95UpperBound", "totalFrames", "stopReason",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row_sha(row):
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def figure_row(fid, source_name, source_row_id, row, metric):
    if metric == "ber":
        raw_num = int(row["payloadErrorBits"])
        raw_den = int(row["totalPayloadBits"])
        raw_y = float(row["ber"])
        formula = "3/totalPayloadBits"
    elif metric == "fer":
        raw_num = int(row["payloadErrorFrames"])
        raw_den = int(row["totalFrames"])
        raw_y = float(row["fer"])
        formula = "3/totalFrames"
    else:
        raw_num = int(row["decodeTimeTotalNs"])
        raw_den = int(row["totalFrames"])
        raw_y = float(row["decodeTimeMeanNs"]) / 1000.0
        formula = "none"
    zero = metric in ("ber", "fer") and raw_y == 0.0
    upper_bound = ZERO_OBSERVED_UPPER_BOUND_FACTOR / raw_den if metric in ("ber", "fer") else raw_y
    plot_y = upper_bound if zero else raw_y
    return {
        "figureId": fid,
        "sourceCsv": source_name,
        "sourceRowId": source_row_id,
        "sourceRowSha256": row_sha(row),
        "caseId": row["caseId"],
        "payloadLength": row["payloadLength"],
        "legendLabel": row["legendLabel"],
        "styleId": row["styleId"],
        "snrIndex": row["snrIndex"],
        "snrDb": row["snrDb"],
        "snrLinear": row["snrLinear"],
        "ebn0Db": row["ebn0Db"],
        "actualRate": row["actualRate"],
        "encodedLength": row["encodedLength"],
        "metric": metric,
        "rawNumerator": raw_num,
        "rawDenominator": raw_den,
        "rawY": f"{raw_y:.17g}",
        "plotY": f"{plot_y:.17g}",
        "isZeroObserved": str(zero).lower(),
        "zeroObservedStatus": "ZERO_OBSERVED_CENSORED" if zero else "OBSERVED_ERROR_RATE",
        "plotSurrogateUsed": str(zero).lower(),
        "plotSurrogateFormula": formula if zero else "none",
        "oneSided95UpperBound": f"{upper_bound:.17g}" if metric in ("ber", "fer") else "none",
        "totalFrames": row["totalFrames"],
        "stopReason": row["stopReason"],
    }


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    raw = read(SOURCE)
    row_ids = {id(row): index + 1 for index, row in enumerate(raw)}
    aggregate = []
    figures = []
    config_hash = sha(CONFIG)
    source_hash = sha(SOURCE)
    for payload, tag, metric, title, ylabel, yscale in FIGURES:
        fid = f"stage07_awgn_dense_formal_{tag}_{'latency' if metric.startswith('decode') else metric}"
        selected = [r for r in raw if int(r["payloadLength"]) == payload]
        data = [figure_row(fid, SOURCE.name, row_ids[id(r)], r, metric) for r in selected]
        data.sort(key=lambda x: (x["caseId"], int(x["snrIndex"])))
        write(PLOTS / f"{fid}_figure_data.csv", data, FIGURE_FIELDS)
        aggregate.extend(data)
        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        for case_id in dict.fromkeys(x["caseId"] for x in data):
            pts = [x for x in data if x["caseId"] == case_id]
            color, line, marker = STYLE[pts[0]["styleId"]]
            if yscale == "log":
                observed = [x for x in pts if x["isZeroObserved"] != "true"]
                if observed:
                    ax.plot([float(x["snrDb"]) for x in observed], [float(x["plotY"]) for x in observed],
                            color=color, linestyle=line, marker=marker, markevery=2,
                            label=pts[0]["legendLabel"])
            else:
                ax.plot([float(x["snrDb"]) for x in pts], [float(x["plotY"]) for x in pts],
                        color=color, linestyle=line, marker=marker, markevery=2,
                        label=pts[0]["legendLabel"])
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_xlim(0.0, 18.0)
        ax.set_xticks([float(x) for x in range(0, 19, 1)])
        ax.set_xticks([x * 0.5 for x in range(0, 37)], minor=True)
        if yscale == "log":
            ax.set_yscale("log")
        ax.grid(True, which="both", linestyle=":", linewidth=0.6)
        ax.legend(loc="upper right")
        fig.tight_layout()
        png = PLOTS / f"{fid}.png"
        fig.savefig(png, dpi=300, format="png", bbox_inches="tight")
        plt.close(fig)
        width, height = png_size(png)
        figures.append({
            "figureId": fid,
            "png": png.name,
            "pngSha256": sha(png),
            "figureData": f"{fid}_figure_data.csv",
            "figureDataSha256": sha(PLOTS / f"{fid}_figure_data.csv"),
            "title": title,
            "xLabel": "SNR (dB)",
            "yLabel": ylabel,
            "xSourceColumn": "snrDb",
            "ySourceColumn": metric,
            "xUnit": "dB",
            "yUnit": "us" if metric.startswith("decode") else "ratio",
            "yScale": yscale,
            "dpi": 300,
            "imageFormat": "png",
            "imageWidth": width,
            "imageHeight": height,
            "legendLocation": "upper right",
            "caseOrder": list(dict.fromkeys(x["caseId"] for x in data)),
            "xMin": 0.0,
            "xMax": 18.0,
            "xStep": 0.5,
            "markEvery": 2,
            "zeroObservedPointRule": "BER/FER raw zero values are censored zero-observation points; log plots omit censored zero-observed points from the main curve to avoid a false error floor.",
        })
    aggregate_path = PLOTS / "stage07_awgn_dense_formal_figure_data.csv"
    write(aggregate_path, aggregate, FIGURE_FIELDS)
    manifest = {
        "stageId": "stage07_awgn_dense_formal",
        "sourceResultsFile": SOURCE.name,
        "sourceResultsSha256": source_hash,
        "plotScript": Path(__file__).name,
        "plotScriptSha256": sha(Path(__file__)),
        "configFile": CONFIG.name,
        "configSha256": config_hash,
        "configHash": config_hash,
        "gitCommit": raw[0]["gitCommit"],
        "pythonVersion": platform.python_version(),
        "matplotlibVersion": matplotlib.__version__,
        "createdAt": platform.node(),
        "zeroSurrogateRule": "raw CSV keeps zero; zero-observed BER/FER points are censored; log plots omit censored zero-observed points from the main curve to avoid a false error floor; 3/raw denominator upper bounds remain in figure-data and published error-floor analysis",
        "zeroObservedUpperBoundFactor": ZERO_OBSERVED_UPPER_BOUND_FACTOR,
        "xTransformFormula": "EbN0_dB = SNR_dB - 10*log10(2*R); sigma2 = 1/10^(SNR_dB/10)",
        "legendMapping": {r["caseId"]: r["legendLabel"] for r in raw},
        "styleMapping": STYLE,
        "aggregateFigureData": aggregate_path.name,
        "aggregateFigureDataSha256": sha(aggregate_path),
        "figures": figures,
    }
    (PLOTS / "stage07_awgn_dense_formal_plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT")


if __name__ == "__main__":
    main()
