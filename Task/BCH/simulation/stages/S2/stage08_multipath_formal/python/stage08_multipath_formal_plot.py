#!/usr/bin/env python3
"""Generate the eight frozen stage08 matplotlib PNGs and their evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PREFIX = "stage08_multipath_formal"
STYLE = {
    "K200_S15": ("分块200", "STYLE_1", "C0", "-", "o"),
    "K200_M255K207": ("255整块200", "STYLE_2", "C1", "--", "s"),
    "K200_M511K421": ("421整块200", "STYLE_3", "C2", "-.", "^"),
    "K200_M511K385": ("385整块200", "STYLE_4", "C3", ":", "D"),
    "K300_S15": ("分块300", "STYLE_1", "C0", "-", "o"),
    "K300_M255K207": ("255双块300", "STYLE_2", "C1", "--", "s"),
    "K300_M511K421": ("421整块300", "STYLE_3", "C2", "-.", "^"),
    "K300_M511K385": ("385整块300", "STYLE_4", "C3", ":", "D"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    stage = Path(__file__).resolve().parents[1]
    source = stage / f"results/{PREFIX}_results.csv"
    rows = read(source)
    plots = stage / "plots"
    plots.mkdir(exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    definitions = [
        (200, "ber", "BER", "200比特BCH多径误码率对比", "log"),
        (200, "fer", "FER", "200比特BCH多径误帧率对比", "log"),
        (200, "decodeTimeMeanNs", "译码时延 (μs)", "200比特BCH多径译码时延对比", "linear"),
        (200, "equalizeTimeMeanNs", "均衡时延 (μs)", "200比特BCH多径均衡时延对比", "linear"),
        (300, "ber", "BER", "300比特BCH多径误码率对比", "log"),
        (300, "fer", "FER", "300比特BCH多径误帧率对比", "log"),
        (300, "decodeTimeMeanNs", "译码时延 (μs)", "300比特BCH多径译码时延对比", "linear"),
        (300, "equalizeTimeMeanNs", "均衡时延 (μs)", "300比特BCH多径均衡时延对比", "linear"),
    ]
    manifest_paths = []
    for payload_length, field, ylabel, title, scale in definitions:
        suffix = {
            "ber": "ber",
            "fer": "fer",
            "decodeTimeMeanNs": "decode_latency",
            "equalizeTimeMeanNs": "equalize_latency",
        }[field]
        stem = f"{PREFIX}_k{payload_length}_{suffix}"
        png = plots / f"{stem}.png"
        figure_csv = plots / f"{stem}_figure_data.csv"
        figure_rows = []
        fig, ax = plt.subplots(figsize=(9.0, 5.8), dpi=140)
        selected_cases = [
            case_id for case_id in STYLE if case_id.startswith(f"K{payload_length}_")
        ]
        for case_id in selected_cases:
            selected = sorted(
                [row for row in rows if row["caseId"] == case_id],
                key=lambda row: float(row["snrDb"]),
            )
            legend, style_id, color, line, marker = STYLE[case_id]
            x = [float(row["snrDb"]) for row in selected]
            y = []
            for row in selected:
                raw = float(row[field])
                is_zero = raw == 0.0
                surrogate = False
                if scale == "log" and is_zero:
                    raw_count = (
                        int(row["totalPayloadBits"])
                        if field == "ber"
                        else int(row["totalFrames"])
                    )
                    plot_value = 0.5 / raw_count
                    surrogate = True
                elif field.endswith("TimeMeanNs"):
                    plot_value = raw / 1000.0
                else:
                    plot_value = raw
                y.append(plot_value)
                figure_rows.append(
                    {
                        "caseId": case_id,
                        "legendLabel": legend,
                        "styleId": style_id,
                        "ebn0Db": row["ebn0Db"],
                        "actualRate": row["actualRate"],
                        "snrLinear": row["snrLinear"],
                        "snrDb": row["snrDb"],
                        "rawY": f"{raw:.17g}",
                        "plotY": f"{plot_value:.17g}",
                        "isZeroObserved": str(is_zero).lower(),
                        "plotSurrogateUsed": str(surrogate).lower(),
                        "plotSurrogateFormula": (
                            "0.5/totalPayloadBits" if surrogate and field == "ber"
                            else "0.5/totalFrames" if surrogate else "NONE"
                        ),
                        "sourceCsv": f"results/{PREFIX}_results.csv",
                        "sourceRowId": f"{case_id}:{row['ebn0Index']}",
                    }
                )
            ax.plot(x, y, label=legend, color=color, linestyle=line, marker=marker)
        ax.set_title(title)
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel(ylabel)
        ax.set_yscale(scale)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(png, format="png", dpi=140)
        plt.close(fig)
        with figure_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(figure_rows[0]))
            writer.writeheader()
            writer.writerows(figure_rows)
        manifest = {
            "plotFile": f"plots/{png.name}",
            "plotType": field,
            "title": title,
            "xLabel": "SNR (dB)",
            "yLabel": ylabel,
            "xSourceColumn": "snrDb",
            "ySourceColumn": field,
            "xTransformFormula": "SNR_dB = EbN0_dB + 10*log10(2*R)",
            "yScale": scale,
            "zeroHandlingRule": "raw zero retained; plotY=0.5/count only for log display",
            "sourceCsv": f"results/{PREFIX}_results.csv",
            "sourceCsvSha256": sha(source),
            "figureDataCsv": f"plots/{figure_csv.name}",
            "figureDataSha256": sha(figure_csv),
            "legendMapping": {case: STYLE[case][0] for case in selected_cases},
            "styleMapping": {
                case: {
                    "styleId": STYLE[case][1],
                    "color": STYLE[case][2],
                    "lineStyle": STYLE[case][3],
                    "marker": STYLE[case][4],
                }
                for case in selected_cases
            },
            "matplotlibVersion": matplotlib.__version__,
            "pythonVersion": platform.python_version(),
            "dpi": 140,
            "imageFormat": "PNG",
            "imageWidth": 1260,
            "imageHeight": 812,
            "plotScript": f"python/{Path(__file__).name}",
            "plotScriptSha256": sha(Path(__file__)),
            "plotFileSha256": sha(png),
            "gitCommit": rows[0]["gitCommit"],
            "configHash": rows[0]["configHash"],
        }
        manifest_path = plots / f"{stem}_plot_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest_paths.append(str(manifest_path.relative_to(stage)).replace("\\", "/"))
    (stage / f"{PREFIX}_plot_manifest.json").write_text(
        json.dumps({"plots": manifest_paths}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("PASS_STAGE08_PLOT_GENERATION plots=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
