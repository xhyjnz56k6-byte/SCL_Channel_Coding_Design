import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "BCH": ROOT / "stage10_bch_formal" / "results" / "formal_results.csv",
    "CC": ROOT / "stage11_cc_formal" / "results" / "formal_results.csv",
}


def weighted_mean(rows, field):
    total_frames = sum(int(row["framesProcessed"]) for row in rows)
    return sum(float(row[field]) * int(row["framesProcessed"]) for row in rows) / total_frames


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stage13_latency_complexity" / "results"
    output = out_dir / "latency_complexity_summary.csv"
    fields = [
        "scheme", "configurationId", "method", "parameter", "comparisonRole",
        "engineeringComparisonGroup", "controlledComparisonGroup", "pureMethodDifferenceAllowed",
        "formalPointCount", "totalFrames", "decodeTimeMeanNsWeighted", "interleaveTimeMeanNsWeighted",
        "deinterleaveTimeMeanNsWeighted", "additionalCpuTimeMeanNsWeighted", "decodeTimeP95NsPointWeighted",
        "interleaveTimeP95NsPointWeighted", "deinterleaveTimeP95NsPointWeighted", "bufferBits",
        "startupDelayBits", "startupDelayTrellisSteps", "bufferFractionOfFrame", "spanBits",
        "spanTrellisSteps", "physicalLatencyClaimAllowed", "sourceAbsolutePath"
    ]
    output_rows = []
    for scheme, source in SOURCES.items():
        rows = list(csv.DictReader(source.open(encoding="utf-8")))
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["configurationId"]].append(row)
        encoded = 285 if scheme == "BCH" else 612
        for config, group in sorted(grouped.items()):
            first = group[0]
            buffer_bits = int(first["bufferBits"])
            span_steps = int(first["spanTrellisSteps"])
            interleave = weighted_mean(group, "interleaveTimeMeanNs")
            deinterleave = weighted_mean(group, "deinterleaveTimeMeanNs")
            output_rows.append({
                "scheme": scheme, "configurationId": config, "method": first["method"],
                "parameter": first["parameter"], "comparisonRole": first["comparisonRole"],
                "engineeringComparisonGroup": first["engineeringComparisonGroup"],
                "controlledComparisonGroup": first["controlledComparisonGroup"],
                "pureMethodDifferenceAllowed": "false", "formalPointCount": len(group),
                "totalFrames": sum(int(row["framesProcessed"]) for row in group),
                "decodeTimeMeanNsWeighted": weighted_mean(group, "decodeTimeMeanNs"),
                "interleaveTimeMeanNsWeighted": interleave,
                "deinterleaveTimeMeanNsWeighted": deinterleave,
                "additionalCpuTimeMeanNsWeighted": interleave + deinterleave,
                "decodeTimeP95NsPointWeighted": weighted_mean(group, "decodeTimeP95Ns"),
                "interleaveTimeP95NsPointWeighted": weighted_mean(group, "interleaveTimeP95Ns"),
                "deinterleaveTimeP95NsPointWeighted": weighted_mean(group, "deinterleaveTimeP95Ns"),
                "bufferBits": buffer_bits, "startupDelayBits": buffer_bits,
                "startupDelayTrellisSteps": span_steps if scheme == "CC" and buffer_bits > 0 else 0,
                "bufferFractionOfFrame": buffer_bits / encoded, "spanBits": first["spanBits"],
                "spanTrellisSteps": span_steps, "physicalLatencyClaimAllowed": "false",
                "sourceAbsolutePath": str(source.resolve())
            })
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(output_rows)
    print(f"PASS_S7_STAGE13_ANALYSIS rows={len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
