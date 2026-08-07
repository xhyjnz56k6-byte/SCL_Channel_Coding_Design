from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Report/data/chapter04/bch"
FIG = ROOT / "Report/figures/bch"
SHIFT = 10.0 * math.log10(2.0)

S1 = ROOT / "Task/BCH/simulation/stages/S1/stage07_awgn_dense_formal/published_results/stage07_awgn_dense_formal_results.csv"
MP = ROOT / "Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/results/stage08_multipath_formal_common_snr_results.csv"
CFO = ROOT / "Task/BCH/simulation/stages/S2/stage10_cfo_formal/results/stage10_cfo_formal_result_summary.csv"
BLOCK = ROOT / "Task/BCH/simulation/stages/S2/stage12_blockage_formal/results/stage12_blockage_formal_result_summary.csv"
BURST = ROOT / "Task/BCH/simulation/stages/S2/stage14_burst_formal/results/stage14_burst_formal_summary.csv"

LABELS = {
    "K200_S15": "分组BCH(15,11)，200 bit",
    "K200_M255K207": "缩短BCH(255,207)，200 bit",
    "K200_M511K421": "缩短BCH(511,421)，200 bit",
    "K200_M511K385": "缩短BCH(511,385)，200 bit",
    "K300_S15": "分组BCH(15,11)，300 bit",
    "K300_M255K207": "双块缩短BCH(255,207)，300 bit",
    "K300_M511K421": "缩短BCH(511,421)，300 bit",
    "K300_M511K385": "缩短BCH(511,385)，300 bit",
}


def setup() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 7.5,
        "figure.dpi": 150,
        "savefig.dpi": 220,
    })


def report_frame(df: pd.DataFrame, source: Path, snr_col: str, eb_col: str | None,
                 es_transform) -> pd.DataFrame:
    out = pd.DataFrame()
    out["caseId"] = df["caseId"]
    out["schemeName"] = df["caseId"].map(LABELS)
    out["payloadLength"] = pd.to_numeric(df["payloadLength"])
    out["encodedLength"] = pd.to_numeric(df["encodedLength"])
    out["actualRate"] = pd.to_numeric(df["actualRate"])
    out["sourceSnrDb"] = pd.to_numeric(df[snr_col])
    out["sourceEbN0Db"] = pd.to_numeric(df[eb_col]) if eb_col else ""
    out["esN0Db"] = es_transform(out)
    out["BER"] = pd.to_numeric(df["ber"])
    out["FER"] = pd.to_numeric(df["fer"])
    frames = "totalFrames" if "totalFrames" in df else "framesProcessed"
    out["processedFrames"] = pd.to_numeric(df[frames])
    out["sourceFile"] = source.relative_to(ROOT).as_posix()
    return out


def draw_metric(df: pd.DataFrame, payload: int, metric: str, title: str, target: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    for case_id, part in df[df.payloadLength == payload].groupby("caseId", sort=False):
        part = part.sort_values("esN0Db")
        visible = part[pd.to_numeric(part[metric]) > 0]
        ax.semilogy(visible.esN0Db, visible[metric], marker="o", markersize=2.6,
                    linewidth=1.25, label=LABELS[case_id])
    ax.set_title(title)
    ax.set_xlabel(r"符号信噪比 $E_s/N_0$（dB）")
    ax.set_ylabel(metric)
    ax.grid(True, which="both", linewidth=0.45, alpha=0.45)
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def draw_two_panel(df: pd.DataFrame, title: str, target: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True)
    for ax, payload in zip(axes, (200, 300)):
        for case_id, part in df[df.payloadLength == payload].groupby("caseId", sort=False):
            part = part.sort_values("esN0Db")
            visible = part[part.FER > 0]
            ax.semilogy(visible.esN0Db, visible.FER, marker="o", markersize=2.3,
                        linewidth=1.15, label=LABELS[case_id])
        ax.set_title(f"{payload} bit电文")
        ax.set_xlabel(r"符号信噪比 $E_s/N_0$（dB）")
        ax.grid(True, which="both", linewidth=0.45, alpha=0.45)
    axes[0].set_ylabel("FER")
    axes[0].legend(fontsize=6.5)
    axes[1].legend(fontsize=6.5)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def threshold_x(part: pd.DataFrame, target: float) -> float | None:
    part = part.sort_values("esN0Db")
    rows = [(float(x), float(y)) for x, y in zip(part.esN0Db, part.FER) if float(y) > 0]
    for (x0, y0), (x1, y1) in zip(rows, rows[1:]):
        if (y0 - target) * (y1 - target) <= 0 and y0 != y1:
            ly0, ly1, lt = math.log10(y0), math.log10(y1), math.log10(target)
            return x0 + (lt - ly0) * (x1 - x0) / (ly1 - ly0)
    return None


def main() -> None:
    setup()
    s1_raw = pd.read_csv(S1)
    s1 = report_frame(s1_raw, S1, "snrDb", "ebn0Db", lambda x: x.sourceSnrDb - SHIFT)
    s1["decodeTimeMeanNs"] = pd.to_numeric(s1_raw["decodeTimeMeanNs"])
    s1["decodeTimeP95Ns"] = pd.to_numeric(s1_raw["decodeTimeP95Ns"])
    s1.to_csv(DATA / "s1_awgn_report_data.csv", index=False, encoding="utf-8-sig")
    draw_metric(s1, 200, "FER", "200 bit电文的AWGN帧错误率", FIG / "s1_awgn_k200_fer.png")
    draw_metric(s1, 300, "FER", "300 bit电文的AWGN帧错误率", FIG / "s1_awgn_k300_fer.png")
    draw_metric(s1, 200, "BER", "200 bit电文的AWGN比特错误率", FIG / "s1_awgn_k200_ber.png")
    draw_metric(s1, 300, "BER", "300 bit电文的AWGN比特错误率", FIG / "s1_awgn_k300_ber.png")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), sharey=True)
    for ax, payload in zip(axes, (200, 300)):
        for case_id, part in s1[s1.payloadLength == payload].groupby("caseId", sort=False):
            part = part.sort_values("esN0Db")
            ax.plot(part.esN0Db, part.decodeTimeMeanNs / 1000.0, linewidth=1.15,
                    label=LABELS[case_id])
        ax.set_title(f"{payload} bit电文")
        ax.set_xlabel(r"符号信噪比 $E_s/N_0$（dB）")
        ax.grid(True, linewidth=0.45, alpha=0.45)
        ax.legend(fontsize=6.5)
    axes[0].set_ylabel("平均译码CPU时间（μs/帧）")
    fig.suptitle("AWGN正式仿真的软件译码时间")
    fig.tight_layout()
    fig.savefig(FIG / "s1_decode_latency.png", bbox_inches="tight")
    plt.close(fig)

    mp_raw = pd.read_csv(MP)
    mp = report_frame(mp_raw, MP, "waveformSnrDb", "derivedEbn0Db", lambda x: x.sourceSnrDb - SHIFT)
    mp.to_csv(DATA / "s2_multipath_report_data.csv", index=False, encoding="utf-8-sig")
    draw_two_panel(mp, "固定实数多径与线性MMSE均衡后的FER", FIG / "s2_multipath_fer.png")

    cfo_raw = pd.read_csv(CFO)
    cfo = report_frame(cfo_raw, CFO, "snrDb", "ebn0Db", lambda x: x.sourceSnrDb)
    cfo.to_csv(DATA / "s2_phase_drift_report_data.csv", index=False, encoding="utf-8-sig")
    draw_two_panel(cfo, "帧内0°至30°线性相位漂移下的FER", FIG / "s2_phase_drift_fer.png")

    block_raw = pd.read_csv(BLOCK)
    block_raw = block_raw[block_raw.experimentType == "SNR"].copy()
    block = report_frame(block_raw, BLOCK, "snrDb", "ebn0Db", lambda x: x.sourceSnrDb)
    block["blockageRatio"] = pd.to_numeric(block_raw["actualBlockageRatio"]).to_numpy()
    block.to_csv(DATA / "s2_blockage_report_data.csv", index=False, encoding="utf-8-sig")
    draw_two_panel(block, "10%连续符号置零遮挡下的FER", FIG / "s2_blockage_fer.png")

    burst_raw = pd.read_csv(BURST)
    burst = pd.DataFrame({
        "caseId": burst_raw.caseId,
        "schemeName": burst_raw.caseId.map(LABELS),
        "payloadLength": pd.to_numeric(burst_raw.payloadLength),
        "encodedLength": pd.to_numeric(burst_raw.encodedLength),
        "actualRate": pd.to_numeric(burst_raw.actualRate),
        "burstLengthBits": pd.to_numeric(burst_raw.burstLengthBits),
        "burstRatio": pd.to_numeric(burst_raw.burstRatio),
        "BER": pd.to_numeric(burst_raw.ber),
        "FER": pd.to_numeric(burst_raw.fer),
        "processedFrames": pd.to_numeric(burst_raw.framesProcessed),
        "sourceFile": BURST.relative_to(ROOT).as_posix(),
    })
    burst.to_csv(DATA / "s2_burst_report_data.csv", index=False, encoding="utf-8-sig")
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True)
    for ax, payload in zip(axes, (200, 300)):
        for case_id, part in burst[burst.payloadLength == payload].groupby("caseId", sort=False):
            ax.plot(part.burstLengthBits, part.FER, marker="o", markersize=2.5,
                    linewidth=1.15, label=LABELS[case_id])
        ax.set_title(f"{payload} bit电文")
        ax.set_xlabel("连续翻转长度（bit）")
        ax.grid(True, linewidth=0.45, alpha=0.45)
        ax.legend(fontsize=6.5)
    axes[0].set_ylabel("FER")
    fig.suptitle("无AWGN、无交织的连续硬比特翻转结果")
    fig.tight_layout()
    fig.savefig(FIG / "s2_burst_fer.png", bbox_inches="tight")
    plt.close(fig)

    rows = []
    for case_id, part in s1.groupby("caseId"):
        for target in (1e-1, 1e-2):
            x = threshold_x(part, target)
            rows.append({"scope": "S1_AWGN", "caseId": case_id, "metric": "FER",
                         "target": target, "esN0DbInterpolated": "" if x is None else f"{x:.6f}",
                         "sourceFile": S1.relative_to(ROOT).as_posix(),
                         "note": "仅在相邻非零正式统计点之间按log10(FER)线性插值"})
    with (DATA / "numeric_thresholds.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
