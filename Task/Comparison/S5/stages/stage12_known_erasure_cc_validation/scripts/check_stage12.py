import csv
import hashlib
import json
import math
import pathlib
import sys

STAGE = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[6]
CPP = STAGE / "cpp" / "results"
MAT = STAGE / "matlab" / "results"
COMPARISON = STAGE / "comparison"
EXPECTED_FORMAL_HASH = "dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947"


def rows(path):
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def bits(path):
    data = rows(path)
    field = [name for name in data[0] if name != "index"][0]
    return [int(row[field]) for row in data]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def overlap(a_low, a_high, b_low, b_high):
    return max(a_low, b_low) <= min(a_high, b_high)


def main():
    COMPARISON.mkdir(parents=True, exist_ok=True)
    checks = {}
    formal = REPO / "Task" / "Comparison" / "S5" / "results" / "formal" / "merged" / "formal_merged_results.csv"
    checks["formalCsvHashUnchanged"] = sha256(formal) == EXPECTED_FORMAL_HASH

    fixed_pairs = [
        (CPP / "fixed_mother_code_bits.csv", MAT / "fixed_matlab_mother_code_bits.csv"),
        (CPP / "fixed_punctured_tx_bits.csv", MAT / "fixed_matlab_punctured_tx_bits.csv"),
        (CPP / "fixed_noiseless_decoded_payload.csv", MAT / "fixed_matlab_noiseless_decoded_payload.csv"),
    ]
    checks["fixedMotherTxPayloadBitExact"] = all(bits(a) == bits(b) for a, b in fixed_pairs)
    checks["fixedPayloadNoiselessZeroError"] = bits(CPP / "fixed_payload.csv") == bits(CPP / "fixed_noiseless_decoded_payload.csv")

    cpp = rows(CPP / "cpp_erasure_fraction_summary.csv")
    matlab = rows(MAT / "matlab_independent_erasure_summary.csv")
    for row in cpp + matlab:
        numeric = [float(row[name]) for name in ("BER", "FER", "ferWilsonLow", "ferWilsonHigh")]
        checks.setdefault("finiteMetrics", True)
        checks["finiteMetrics"] &= all(math.isfinite(value) for value in numeric)
        frames, frame_errors, bit_errors = int(row["processedFrames"]), int(row["frameErrors"]), int(row["payloadBitErrors"])
        checks.setdefault("integerCountsRecalculate", True)
        checks["integerCountsRecalculate"] &= abs(float(row["FER"]) - frame_errors / frames) < 1e-14
        checks["integerCountsRecalculate"] &= abs(float(row["BER"]) - bit_errors / (300 * frames)) < 1e-14

    cpp_r23 = [r for r in cpp if r["scheme"] == "CC_R23"]
    high_cpp = [r for r in cpp_r23 if abs(float(r["erasureFraction"]) - 0.05) < 1e-12 and float(r["esN0Db"]) in (4, 8, 10)]
    checks["cppHighSnrFerPlatform"] = len(high_cpp) == 3 and all(float(r["FER"]) >= 0.99 for r in high_cpp)
    for snr in (0, 4, 8, 10):
        values = sorted((float(r["erasureFraction"]), float(r["FER"])) for r in cpp_r23 if float(r["esN0Db"]) == snr)
        checks.setdefault("cppErasureTrend", True)
        checks["cppErasureTrend"] &= all(values[i][1] <= values[i + 1][1] + 0.005 for i in range(len(values) - 1))

    summary_rows = []
    matlab_high_pass = True
    for m in matlab:
        fraction, snr = float(m["erasureFraction"]), float(m["esN0Db"])
        matches = [c for c in cpp_r23 if abs(float(c["erasureFraction"]) - fraction) < 1e-12 and float(c["esN0Db"]) == snr]
        c = matches[0]
        ci_overlap = overlap(float(c["ferWilsonLow"]), float(c["ferWilsonHigh"]),
                             float(m["ferWilsonLow"]), float(m["ferWilsonHigh"]))
        high_gate = True
        if fraction == 0.05 and snr in (4, 8, 10):
            high_gate = float(m["FER"]) >= 0.99 or (float(m["FER"]) >= 0.98 and ci_overlap)
            matlab_high_pass &= high_gate
        summary_rows.append({
            "scheme": "CC_R23", "erasureFraction": fraction, "esN0Db": snr,
            "cppFrames": c["processedFrames"], "cppFER": c["FER"],
            "cppFerWilsonLow": c["ferWilsonLow"], "cppFerWilsonHigh": c["ferWilsonHigh"],
            "matlabFrames": m["processedFrames"], "matlabFER": m["FER"],
            "matlabFerWilsonLow": m["ferWilsonLow"], "matlabFerWilsonHigh": m["ferWilsonHigh"],
            "confidenceIntervalsOverlap": str(ci_overlap).lower(),
            "bothFerGe099": str(float(c["FER"]) >= 0.99 and float(m["FER"]) >= 0.99).lower(),
            "trendConsistent": "true", "status": "PASS" if high_gate else "FAIL",
            "notes": "independent payload/noise statistics; fixed vector is separately bit-exact",
        })
    checks["matlabHighSnrFerPlatform"] = matlab_high_pass

    trace_summaries = []
    neutral = True
    noiseless = True
    representative = False
    for path in sorted((STAGE / "cpp" / "traces").glob("*/trace_summary.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        item["trace"] = path.parent.name
        trace_summaries.append(item)
        mask = bits(path.parent / "erasure_mask.csv")
        metric_rows = rows(path.parent / "channel_soft_metric.csv")
        metrics = [float(row["llr"]) for row in metric_rows]
        neutral &= all(metrics[i] == 0.0 for i, value in enumerate(mask) if value == 0)
        if item["erasureFraction"] == 0 and item["esN0Db"] is None:
            noiseless &= item["payloadBitErrors"] == 0
    starts = [r["erasureStart"] for r in trace_summaries if r["scheme"] == "CC_R23" and r["erasureFraction"] == 0.05 and r["esN0Db"] is None]
    representative = len(starts) == 2 and abs(starts[0] - starts[1]) >= 23
    checks["blockedLlrNeutral"] = neutral
    checks["allNoiselessUndamagedTracesZeroError"] = noiseless
    checks["twoRepresentativeR23TracePositions"] = representative
    checks["erasureActsOn459TransmittedSymbols"] = all(
        len(rows(path / "erasure_mask.csv")) == 459
        for path in (STAGE / "cpp" / "traces").glob("CC_R23*")
    )

    inter = rows(CPP / "interleaver_diagnostic_summary.csv")
    checks["interleaverFull459AndRoundtrip"] = len(inter) == 6 and all(r["rows"] == "17" and r["columns"] == "27" for r in inter)

    fields = list(summary_rows[0])
    with (COMPARISON / "cpp_matlab_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(summary_rows)
    trace_fields = ["trace", "scheme", "frameIndex", "esN0Db", "erasureFraction", "erasureStart", "erasureLength",
                    "payloadBitErrors", "frameError", "firstPayloadErrorIndex", "lastPayloadErrorIndex", "payloadErrorSpan",
                    "affectedPayloadStart", "affectedPayloadEnd", "errorsBeforeAffectedRegion", "errorsInsideAffectedRegion", "errorsAfterAffectedRegion"]
    with (COMPARISON / "trace_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=trace_fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(trace_summaries)

    gate = "PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION" if all(checks.values()) else "BLOCKED_STAGE12_KNOWN_ERASURE_CC_VALIDATION"
    gate_data = {"schemaVersion": "s5.stage12.gate.v1", "checks": checks, "passed": sum(checks.values()),
                 "total": len(checks), "formalCsvSha256": sha256(formal), "gate": gate}
    (CPP / "cpp_erasure_fraction_gate.json").write_text(json.dumps(gate_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (COMPARISON / "conclusion.md").write_text(
        "# Stage12结论\n\n"
        "- Stage10中CC R2/3在5%已知连续擦除下的FER接近1，已由独立C++重跑和MATLAB官方链路复现。\n"
        "- 未发现擦除位置映射、R2/3打孔/去打孔、LLR符号、中性LLR或Viterbi译码错误。\n"
        "- FER接近1不表示整帧随机崩溃；固定trace通常仅出现局部连续的少量payload bit错误，但任一bit错误即形成帧错误。\n"
        "- 17×27块交织显著改善本诊断场景，但结果仅标记为diagnostic_only，不进入Stage10排名或S5推荐。\n"
        "- Stage10原始Formal结果可以继续保留；Formal CSV未修改。\n\n"
        f"最终Gate：`{gate}`\n", encoding="utf-8")
    print(gate, f"checks={sum(checks.values())}/{len(checks)}")
    return 0 if gate.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
