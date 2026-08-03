#!/usr/bin/env python3
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = pathlib.Path(__file__).resolve().parents[5]
S5 = ROOT / "Task" / "Comparison" / "S5"
SOURCE = S5 / "results" / "formal" / "merged" / "formal_merged_results.csv"
OUTPUT = S5 / "results" / "stage11"
SCRIPT = pathlib.Path(__file__).resolve()
GROUPS = ("RATE_NEAR_2_3", "RATE_NEAR_1_2")
CHANNELS = (
    "AWGN", "FIXED_MULTIPATH_REAL_MMSE", "CFO_30_DEG",
    "LINEAR_TIME_VARYING_FREQUENCY", "KNOWN_BLOCKAGE_5_PERCENT",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB",
)
SCHEME_ORDER = (
    "CC_R23_BLOCK_FLOAT", "LDPC_BG2_N480_NMS",
    "CC_R12_BLOCK_FLOAT", "LDPC_BG2_N640_NMS",
)
LEGEND = {
    "CC_R23_BLOCK_FLOAT": "卷积码 R2/3", "LDPC_BG2_N480_NMS": "LDPC N480",
    "CC_R12_BLOCK_FLOAT": "卷积码 R1/2", "LDPC_BG2_N640_NMS": "LDPC N640",
}
CHANNEL_TITLE = {
    "AWGN": "AWGN", "FIXED_MULTIPATH_REAL_MMSE": "固定多径",
    "CFO_30_DEG": "30°载波频偏", "LINEAR_TIME_VARYING_FREQUENCY": "多普勒频移",
    "KNOWN_BLOCKAGE_5_PERCENT": "短时遮挡（5%）",
    "UNKNOWN_BURST_5_PERCENT_ISR_10DB": "5%未知突发干扰（ISR=10 dB）",
}
GROUP_TITLE = {"RATE_NEAR_2_3": "近2/3码率组", "RATE_NEAR_1_2": "近1/2码率组", "LDPC_ONLY": "LDPC"}


def configure_chinese_font():
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise RuntimeError("BLOCKED: no approved Chinese font is available")


def sha256(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with pathlib.Path(path).open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, values):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with pathlib.Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(values)


def group_schemes(group):
    return SCHEME_ORDER[:2] if group == GROUPS[0] else SCHEME_ORDER[2:]


def make_plot(rows, figure_id, title, group, channel, y_fields, y_labels,
              log_axis=False, ylabel="", extra_filter=None):
    directory = OUTPUT / "plots" / figure_id
    directory.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    write_csv(directory / "figure_data.csv", fields, rows)
    plt.figure(figsize=(8.6, 5.6), dpi=150)
    curves = 0
    styles = ("-o", "--s", "-.^", ":D", "-v", "--P", "-.X", ":<", "->", "--h")
    for index, (field, label) in enumerate(zip(y_fields, y_labels)):
        values = sorted(rows, key=lambda r: float(r["esN0Db"]))
        x = [float(r["esN0Db"]) for r in values]
        y_raw = [float(r[field]) for r in values]
        y = [math.nan if log_axis and value == 0 else value for value in y_raw]
        plt.plot(x, y, styles[index % len(styles)], linewidth=1.4, markersize=3.5, label=label)
        curves += 1
    if log_axis:
        plt.yscale("log")
    plt.xlabel("符号信噪比 Es/N0（dB）")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    note = "观测零错误点未在对数坐标中绘制。" if log_axis else ""
    if note:
        plt.figtext(0.5, 0.01, note, ha="center", fontsize=8)
    plt.tight_layout(rect=(0, 0.035 if note else 0, 1, 1))
    plt.savefig(directory / "figure.png")
    plt.close()
    config_hash = rows[0]["configHash"]
    manifest = {
        "figureId": figure_id, "title": title,
        "sourceFormalCsv": SOURCE.relative_to(ROOT).as_posix(),
        "sourceFormalCsvSha256": sha256(SOURCE),
        "filterConditions": extra_filter or {"group": group, "channel": channel},
        "xColumn": "esN0Db", "yColumns": y_fields, "units": {"x": "dB", "y": ylabel},
        "logAxis": log_axis,
        "zeroHandling": "retain zero in CSV; omit zero from log plot" if log_axis else "plot exact value",
        "interpolation": "NONE", "smoothing": "NONE", "plotType": "LINE",
        "language": "zh-CN", "chineseFont": CHINESE_FONT,
        "schemeOrder": list(SCHEME_ORDER), "channel": channel, "comparisonGroup": group,
        "configHash": config_hash, "scriptPath": SCRIPT.relative_to(ROOT).as_posix(),
        "scriptSha256": sha256(SCRIPT), "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "curveCount": curves,
    }
    (directory / "plot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    data_ok = True
    for row in rows:
        snr = float(row["esN0Db"])
        for field in y_fields:
            parts = field.split("__")
            if parts[0] == "deltaFer":
                source_channel, source_scheme = parts[1], parts[2]
                impaired = next((r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == source_channel
                                 and r["scheme"] == source_scheme and float(r["esN0Db"]) == snr), None)
                awgn = next((r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == "AWGN"
                             and r["scheme"] == source_scheme and float(r["esN0Db"]) == snr), None)
                expected = float(impaired["FER"]) - float(awgn["FER"]) if impaired and awgn else math.nan
            else:
                metric, source_scheme = parts[0], parts[1]
                source = next((r for r in FORMAL_ROWS if r["channel"] == channel and r["scheme"] == source_scheme
                               and float(r["esN0Db"]) == snr), None)
                expected = float(source[metric]) if source else math.nan
            data_ok &= math.isfinite(expected) and float(row[field]) == expected
    snr_complete = len(rows) == 31 and len({float(r["esN0Db"]) for r in rows}) == 31
    finite = all(math.isfinite(float(r[field])) for r in rows for field in y_fields)
    nonnegative = all(float(r[field]) >= 0 for r in rows for field in y_fields
                      if not field.startswith("deltaFer__"))
    checks = {
        "sourceCsvExists": SOURCE.exists(), "sourceHashMatches": manifest["sourceFormalCsvSha256"] == sha256(SOURCE),
        "dataRowsExactFromSource": data_ok, "noAddedSnr": data_ok, "berFerUnmodified": data_ok,
        "nonNegative": nonnegative, "noNanInf": finite, "zeroNotReplaced": data_ok,
        "noBarChart": True, "noSmoothing": True, "legendCurveCountMatches": curves == len(y_fields),
        "complete31PointGridPerCurve": snr_complete,
        "no10PercentStressInFormal": all(r["channel"] != "KNOWN_BLOCKAGE_10_PERCENT" for r in rows),
    }
    passed = all(checks.values())
    (directory / "plot_check.md").write_text(
        "# Plot check\n\n" + "\n".join(f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in checks.items())
        + f"\n\nGate: **{'PASS' if passed else 'FAIL'}**\n", encoding="utf-8")
    hashes = []
    for name in ("figure.png", "figure_data.csv", "plot_manifest.json", "plot_check.md"):
        hashes.append(f"{sha256(directory / name)}  {name}")
    (directory / "sha256.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    return passed


def interpolate_target(points, target):
    points = sorted((float(r["esN0Db"]), float(r["FER"])) for r in points)
    log_target = math.log10(target)
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if y1 <= 0 or y2 <= 0 or not ((y1 >= target >= y2) or (y2 >= target >= y1)):
            continue
        if y1 == y2:
            continue
        x = x1 + (log_target - math.log10(y1)) * (x2 - x1) / (math.log10(y2) - math.log10(y1))
        return {"leftEsN0": x1, "rightEsN0": x2, "leftFer": y1, "rightFer": y2, "snr": x}
    return None


def tables():
    latency_rows = []
    robustness_rows = []
    recommendations = []
    loss_rows = []
    by = {}
    for row in FORMAL_ROWS:
        by.setdefault((row["channel"], row["group"], row["scheme"]), []).append(row)
    for (channel, group, scheme), values in sorted(by.items()):
        awgn = by[("AWGN", group, scheme)]
        avg_fer = sum(float(r["FER"]) for r in values) / 31
        avg_ber = sum(float(r["BER"]) for r in values) / 31
        avg_decode = sum(float(r["avgDecodeTimeUs"]) for r in values) / 31
        p95_decode = sum(float(r["p95DecodeTimeUs"]) for r in values) / 31
        max_decode = max(float(r["maxDecodeTimeUs"]) for r in values)
        avg_receiver = sum(float(r["avgTotalReceiverAlgorithmTimeUs"]) for r in values) / 31
        p95_receiver = sum(float(r["p95TotalReceiverAlgorithmTimeUs"]) for r in values) / 31
        latency_rows.append({"channel": channel, "group": group, "scheme": scheme,
                             "meanAvgDecodeTimeUs": avg_decode, "meanP95DecodeTimeUs": p95_decode,
                             "maxDecodeTimeUs": max_decode,
                             "meanAvgTotalReceiverAlgorithmTimeUs": avg_receiver,
                             "meanP95TotalReceiverAlgorithmTimeUs": p95_receiver})
        delta_fer = sum(float(v["FER"]) - float(a["FER"]) for v, a in zip(sorted(values, key=lambda r: float(r["esN0Db"])),
                                                                          sorted(awgn, key=lambda r: float(r["esN0Db"])))) / 31
        delta_ber = sum(float(v["BER"]) - float(a["BER"]) for v, a in zip(sorted(values, key=lambda r: float(r["esN0Db"])),
                                                                          sorted(awgn, key=lambda r: float(r["esN0Db"])))) / 31
        ldpc = values[0]["iterationsApplicable"] == "true"
        robustness_rows.append({"channel": channel, "group": group, "scheme": scheme,
                                "meanFER": avg_fer, "meanBER": avg_ber,
                                "meanDeltaFerVsOwnAwgn": delta_fer, "meanDeltaBerVsOwnAwgn": delta_ber,
                                "meanIterations": (sum(float(r["avgIterations"]) for r in values) / 31 if ldpc else "NA"),
                                "meanMaxIterationRate": (sum(float(r["maxIterationRate"]) for r in values) / 31 if ldpc else "NA"),
                                "interpretation": "No unified robustness score is constructed."})
        if channel != "AWGN":
            for target in (0.1, 0.01):
                a = interpolate_target(awgn, target)
                c = interpolate_target(values, target)
                loss_rows.append({
                    "channel": channel, "group": group, "scheme": scheme, "targetFer": target,
                    "awgnLeftEsN0": a["leftEsN0"] if a else "", "awgnRightEsN0": a["rightEsN0"] if a else "",
                    "awgnLeftFer": a["leftFer"] if a else "", "awgnRightFer": a["rightFer"] if a else "",
                    "channelLeftEsN0": c["leftEsN0"] if c else "", "channelRightEsN0": c["rightEsN0"] if c else "",
                    "channelLeftFer": c["leftFer"] if c else "", "channelRightFer": c["rightFer"] if c else "",
                    "awgnInterpolatedEsN0": a["snr"] if a else "", "channelInterpolatedEsN0": c["snr"] if c else "",
                    "channelLossDb": c["snr"] - a["snr"] if a and c else "",
                    "coveredByData": bool(a and c),
                    "reasonIfUnavailable": "" if a and c else "No adjacent nonzero measured points bracket target; no extrapolation.",
                })
    for channel in CHANNELS:
        for group in GROUPS:
            schemes = group_schemes(group)
            robust = [r for r in robustness_rows if r["channel"] == channel and r["group"] == group]
            latency = [r for r in latency_rows if r["channel"] == channel and r["group"] == group]
            candidates = []
            for scheme in schemes:
                values = by[(channel, group, scheme)]
                awgn = by[("AWGN", group, scheme)]
                fer01 = interpolate_target(values, 0.1)
                fer001 = interpolate_target(values, 0.01)
                awgn01 = interpolate_target(awgn, 0.1)
                loss01 = fer01["snr"] - awgn01["snr"] if fer01 and awgn01 else None
                lat = next(r for r in latency if r["scheme"] == scheme)
                high = [float(r["FER"]) for r in values if 6.0 <= float(r["esN0Db"]) <= 10.0]
                candidates.append({"scheme": scheme, "fer01": fer01, "fer001": fer001, "loss01": loss01,
                                   "lat": lat, "highFer": sum(high) / len(high)})
            if any(c["fer01"] for c in candidates):
                def rank(c):
                    return (0 if c["fer01"] else 1, 0 if c["fer001"] else 1,
                            c["fer01"]["snr"] if c["fer01"] else math.inf,
                            c["fer001"]["snr"] if c["fer001"] else math.inf,
                            c["loss01"] if c["loss01"] is not None else math.inf,
                            c["lat"]["meanAvgDecodeTimeUs"], c["lat"]["meanP95DecodeTimeUs"], c["lat"]["maxDecodeTimeUs"])
                selected = min(candidates, key=rank)
                primary = "优先比较FER=0.1/0.01覆盖与达到目标所需Es/N0"
                confidence = "HIGH" if all(c["fer01"] is not None for c in candidates) else "MEDIUM"
            else:
                selected = min(candidates, key=lambda c: (c["highFer"], c["lat"]["meanAvgDecodeTimeUs"]))
                primary = "双方均未覆盖FER=0.1；比较6–10 dB实测FER"
                confidence = "LOW"
            recommendations.append({
                "channel": channel, "comparisonGroup": group, "recommendedScheme": selected["scheme"],
                "primaryCriterion": primary, "fer01Covered": selected["fer01"] is not None,
                "fer001Covered": selected["fer001"] is not None,
                "requiredEsN0AtFer01": selected["fer01"]["snr"] if selected["fer01"] else "",
                "requiredEsN0AtFer001": selected["fer001"]["snr"] if selected["fer001"] else "",
                "channelLossAtFer01": selected["loss01"] if selected["loss01"] is not None else "",
                "avgDecodeLatencyUs": selected["lat"]["meanAvgDecodeTimeUs"],
                "p95DecodeLatencyUs": selected["lat"]["meanP95DecodeTimeUs"],
                "maxDecodeLatencyUs": selected["lat"]["maxDecodeTimeUs"],
                "recommendationConfidence": confidence,
                "reason": primary,
                "limitations": ("仅适用于5%短时遮挡Formal；10%历史结果仅为压力场景。"
                                if channel == "KNOWN_BLOCKAGE_5_PERCENT" else "仅适用于冻结的S5受控模型，不外推为真实卫星信道结论。"),
            })
    write_csv(OUTPUT / "s5_latency_comparison.csv", list(latency_rows[0]), latency_rows)
    write_csv(OUTPUT / "s5_robustness_summary.csv", list(robustness_rows[0]), robustness_rows)
    write_csv(OUTPUT / "s5_channel_loss_table.csv", list(loss_rows[0]), loss_rows)
    write_csv(OUTPUT / "s5_scenario_recommendation.csv", list(recommendations[0]), recommendations)


def main():
    global FORMAL_ROWS
    if not SOURCE.exists():
        raise RuntimeError("Formal merged CSV is missing")
    FORMAL_ROWS = read_csv(SOURCE)
    if len(FORMAL_ROWS) != 744:
        raise RuntimeError(f"Formal row count {len(FORMAL_ROWS)} != 744")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    gates = []
    for group in GROUPS:
        for channel in CHANNELS:
            selected = [r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == channel]
            for metric in ("BER", "FER"):
                figure_id = f"{group.lower()}__{channel.lower()}__{metric.lower()}"
                fields = [metric + "__" + scheme for scheme in group_schemes(group)]
                wide = []
                for snr in sorted({float(r["esN0Db"]) for r in selected}):
                    base = next(r for r in selected if float(r["esN0Db"]) == snr)
                    row = dict(base)
                    for scheme, field in zip(group_schemes(group), fields):
                        row[field] = next(r[metric] for r in selected if float(r["esN0Db"]) == snr and r["scheme"] == scheme)
                    wide.append(row)
                gates.append(make_plot(wide, figure_id,
                    f"{CHANNEL_TITLE[channel]}下{GROUP_TITLE[group]}{'误码率' if metric == 'BER' else '误帧率'}对比", group, channel, fields,
                    [LEGEND[s] for s in group_schemes(group)], True, "误码率 BER" if metric == "BER" else "误帧率 FER"))
            timing_metrics = (
                ("avgDecodeTimeUs", "平均译码时延（μs）"),
                ("p95DecodeTimeUs", "P95译码时延（μs）"),
                ("avgTotalReceiverAlgorithmTimeUs", "平均接收机算法时延（μs）"),
                ("p95TotalReceiverAlgorithmTimeUs", "P95接收机算法时延（μs）"),
            )
            for metric, label in timing_metrics:
                figure_id = f"{group.lower()}__{channel.lower()}__{metric.lower()}"
                fields = [metric + "__" + scheme for scheme in group_schemes(group)]
                wide = []
                for snr in sorted({float(r["esN0Db"]) for r in selected}):
                    base = next(r for r in selected if float(r["esN0Db"]) == snr)
                    row = dict(base)
                    for scheme, field in zip(group_schemes(group), fields):
                        row[field] = next(r[metric] for r in selected if float(r["esN0Db"]) == snr and r["scheme"] == scheme)
                    wide.append(row)
                gates.append(make_plot(wide, figure_id, f"{CHANNEL_TITLE[channel]}下{GROUP_TITLE[group]}{label}对比", group, channel,
                                       fields, [LEGEND[s] for s in group_schemes(group)], False, label))
    for channel in CHANNELS:
        ldpc_rows = [r for r in FORMAL_ROWS if r["channel"] == channel and r["iterationsApplicable"] == "true"]
        for metric, label in (("avgIterations", "平均译码迭代次数"),
                              ("maxIterationRate", "最大迭代帧比例")):
            fields = [metric + "__" + scheme for scheme in ("LDPC_BG2_N480_NMS", "LDPC_BG2_N640_NMS")]
            wide = []
            for snr in sorted({float(r["esN0Db"]) for r in ldpc_rows}):
                base = next(r for r in ldpc_rows if float(r["esN0Db"]) == snr)
                row = dict(base)
                for scheme, field in zip(("LDPC_BG2_N480_NMS", "LDPC_BG2_N640_NMS"), fields):
                    row[field] = next(r[metric] for r in ldpc_rows if float(r["esN0Db"]) == snr and r["scheme"] == scheme)
                wide.append(row)
            gates.append(make_plot(wide, f"ldpc__{channel.lower()}__{metric.lower()}",
                                   f"{CHANNEL_TITLE[channel]}下LDPC{label}", "LDPC_ONLY", channel, fields,
                                   ["LDPC N480", "LDPC N640"], False, label,
                                   {"channel": channel, "iterationsApplicable": True}))
    for group in GROUPS:
        fields = []
        labels = []
        wide = []
        for channel in CHANNELS[1:]:
            for scheme in group_schemes(group):
                fields.append(f"deltaFer__{channel}__{scheme}")
                labels.append(f"{CHANNEL_TITLE[channel]} / {LEGEND[scheme]}")
        for snr in [half / 2 for half in range(-10, 21)]:
            base = next(r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == "AWGN"
                        and r["scheme"] == group_schemes(group)[0] and float(r["esN0Db"]) == snr)
            row = dict(base)
            for channel in CHANNELS[1:]:
                for scheme in group_schemes(group):
                    channel_row = next(r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == channel
                                       and r["scheme"] == scheme and float(r["esN0Db"]) == snr)
                    awgn_row = next(r for r in FORMAL_ROWS if r["group"] == group and r["channel"] == "AWGN"
                                    and r["scheme"] == scheme and float(r["esN0Db"]) == snr)
                    row[f"deltaFer__{channel}__{scheme}"] = float(channel_row["FER"]) - float(awgn_row["FER"])
            wide.append(row)
        gates.append(make_plot(wide, f"{group.lower()}__deltafer", f"{GROUP_TITLE[group]}相对AWGN的误帧率劣化",
                               group, "NON_AWGN", fields, labels, False, "相对AWGN的误帧率劣化",
                               {"group": group, "definition": "channel FER - own-scheme AWGN FER"}))
    tables()
    gate = "PASS_S5_PLOT_AUDIT" if all(gates) else "FAIL_S5_PLOT_AUDIT"
    (OUTPUT / "plot_gate.txt").write_text(gate + "\n", encoding="utf-8")
    (OUTPUT / "plot_audit_summary.json").write_text(json.dumps({
        "schemaVersion": "s5.plot_audit_summary.v1", "figureCount": len(gates),
        "passedFigures": sum(gates), "sourceFormalCsvSha256": sha256(SOURCE), "gate": gate,
    }, indent=2) + "\n", encoding="utf-8")
    print(gate, f"figures={len(gates)}")
    return 0 if gate == "PASS_S5_PLOT_AUDIT" else 1


FORMAL_ROWS = []
CHINESE_FONT = configure_chinese_font()
if __name__ == "__main__":
    raise SystemExit(main())
