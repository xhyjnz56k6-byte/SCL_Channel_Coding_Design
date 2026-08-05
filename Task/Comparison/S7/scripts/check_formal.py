from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


EXPECTED = {
    "BCH": {"BCH_NONE", "BCH_CODEBLOCK_D19", "BCH_ROW_COLUMN_R15", "BCH_GLOBAL_PSEUDO_285"},
    "CC": {"CC_NONE", "CC_SHORT_D8_RECOMMENDED", "CC_PSEUDO_128_RECOMMENDED", "CC_SHORT_D16_CONTROL_128"},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_formal.py BCH|CC RESULTS_DIRECTORY")
    scheme = sys.argv[1]
    directory = Path(sys.argv[2]).resolve()
    require(scheme in EXPECTED, "invalid scheme")
    raw = directory / "formal_results.csv"
    with raw.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 2232, f"expected 2232 rows, got {len(rows)}")

    groups = defaultdict(list)
    numeric = ["sigmaSquared", "BER", "FER", "berZeroUpperBound", "ferZeroUpperBound",
               "decodeTimeMeanNs", "decodeTimeMedianNs", "decodeTimeP95Ns", "decodeTimeP99Ns", "decodeTimeMaxNs",
               "interleaveTimeMeanNs", "interleaveTimeP95Ns", "interleaveTimeMaxNs",
               "deinterleaveTimeMeanNs", "deinterleaveTimeP95Ns", "deinterleaveTimeMaxNs"]
    for row in rows:
        require(row["scheme"] == scheme, "scheme mismatch")
        for field in numeric:
            require(math.isfinite(float(row[field])), f"NaN/Inf {field}")
        frames, total_bits = int(row["framesProcessed"]), int(row["totalBits"])
        bit_errors, frame_errors = int(row["bitErrors"]), int(row["frameErrors"])
        payload = 200 if scheme == "BCH" else 300
        require(total_bits == frames * payload, "totalBits mismatch")
        require(abs(float(row["BER"]) - bit_errors / total_bits) <= 1e-15, "BER mismatch")
        require(abs(float(row["FER"]) - frame_errors / frames) <= 1e-15, "FER mismatch")
        require(1000 <= frames <= 50000, "illegal frame count")
        require((frames == 50000) or frame_errors >= 200, "illegal stop condition")
        require(float(row["decodeTimeMedianNs"]) <= float(row["decodeTimeP95Ns"]) <=
                float(row["decodeTimeP99Ns"]) <= float(row["decodeTimeMaxNs"]), "decode quantile order")
        require(float(row["interleaveTimeP95Ns"]) <= float(row["interleaveTimeMaxNs"]), "interleave quantile order")
        require(float(row["deinterleaveTimeP95Ns"]) <= float(row["deinterleaveTimeMaxNs"]), "deinterleave quantile order")
        require(row["pureMethodDifferenceAllowed"] == "false", "pure method flag must remain false")
        if bit_errors == 0:
            require(float(row["BER"]) == 0 and float(row["berZeroUpperBound"]) > 0, "BER zero policy")
        else:
            require(float(row["berZeroUpperBound"]) == 0, "nonzero BER upper bound field")
        if frame_errors == 0:
            require(float(row["FER"]) == 0 and float(row["ferZeroUpperBound"]) > 0, "FER zero policy")
        else:
            require(float(row["ferZeroUpperBound"]) == 0, "nonzero FER upper bound field")
        key = (row["EsN0Db"], row["burstRatioRequested"], row["burstPositionType"])
        groups[key].append(row)

    require(len(groups) == 558, f"expected 558 groups, got {len(groups)}")
    require(len({row["EsN0Db"] for row in rows}) == 31, "Es/N0 grid incomplete")
    require({row["burstRatioRequested"] for row in rows} == {"0.02", "0.050000000000000003", "0.10000000000000001"}, "ratio grid mismatch")
    require({row["burstPositionType"] for row in rows} == {"HEAD", "QUARTER", "MIDDLE", "THREE_QUARTER", "TAIL", "RANDOM"}, "position grid mismatch")
    for key, group in groups.items():
        require({row["configurationId"] for row in group} == EXPECTED[scheme], f"config set mismatch {key}")
        for field in ("framesProcessed", "payloadChecksum", "noiseChecksum", "burstStartChecksum", "frameSequenceHash", "configHash"):
            require(len({row[field] for row in group}) == 1, f"paired fairness mismatch {key} {field}")

    if scheme == "CC":
        by_id = {row["configurationId"]: row for row in rows[:4]}
        # Check globally rather than relying on first group ordering.
        for row in rows:
            identifier = row["configurationId"]
            if identifier in {"CC_SHORT_D8_RECOMMENDED", "CC_PSEUDO_128_RECOMMENDED"}:
                require(row["engineeringComparisonGroup"] == "CC_RECOMMENDED_ENGINEERING_CONFIG", "engineering group missing")
            if identifier in {"CC_SHORT_D16_CONTROL_128", "CC_PSEUDO_128_RECOMMENDED"}:
                require(row["controlledComparisonGroup"] == "CC_EQUAL_SPAN_128" and row["spanTrellisSteps"] == "128", "controlled 128 group mismatch")
        del by_id

    manifest = json.loads((directory / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    require(manifest["status"] == "COMPLETE" and manifest["completedGroups"] == 558, "checkpoint manifest incomplete")
    validation = {
        "status": "PASS",
        "scheme": scheme,
        "rowCount": len(rows),
        "groupCount": len(groups),
        "zeroBerRows": sum(float(row["BER"]) == 0 for row in rows),
        "zeroFerRows": sum(float(row["FER"]) == 0 for row in rows),
        "rawCsvAbsolutePath": str(raw),
        "checkpointAbsolutePath": str((directory / "checkpoint.bin").resolve()),
        "configHash": rows[0]["configHash"],
        "mergeStatus": "NOT_MERGED",
    }
    (directory / "formal_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_S7_{scheme}_FORMAL rows={len(rows)} groups={len(groups)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_FORMAL_CHECKER: {exc}", file=sys.stderr)
        raise

