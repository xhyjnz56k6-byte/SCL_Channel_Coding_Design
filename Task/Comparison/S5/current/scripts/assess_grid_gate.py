#!/usr/bin/env python3
import csv
import json
import math
import pathlib
import sys
from collections import defaultdict


def wilson_half_width(errors: int, frames: int) -> float:
    z = 1.959963984540054
    p = errors / frames
    denominator = 1.0 + z * z / frames
    return z * math.sqrt(p * (1.0 - p) / frames + z * z / (4.0 * frames * frames)) / denominator


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: assess_grid_gate.py GRID.csv REPORT.json", file=sys.stderr)
        return 2
    rows = list(csv.DictReader(pathlib.Path(sys.argv[1]).open(encoding="utf-8")))
    by_point = {(r["group"], r["channel"], r["scheme"], r["esN0Db"]): r for r in rows}
    groups = sorted({r["group"] for r in rows})
    channels = sorted({r["channel"] for r in rows})
    failures = []
    advisories = []
    checks = []

    curves = defaultdict(list)
    joint = defaultdict(list)
    for row in rows:
        fer = float(row["FER"])
        curves[(row["group"], row["channel"], row["scheme"])].append(fer)
        joint[(row["group"], row["channel"])].append(fer)
    for key, values in sorted(curves.items()):
        if all(v == 0.0 for v in values):
            advisories.append({"type": "SINGLE_SCHEME_ALL_ZERO", "key": key})
        if all(v >= 0.99 for v in values):
            advisories.append({"type": "SINGLE_SCHEME_ALL_GE_0_99", "key": key})
    for key, values in sorted(joint.items()):
        status = "PASS"
        if all(v == 0.0 for v in values):
            status = "FAIL_ALL_ZERO"
            failures.append({"type": status, "key": key})
        elif all(v >= 0.99 for v in values):
            status = "FAIL_ALL_GE_0_99"
            failures.append({"type": status, "key": key})
        checks.append({"check": "JOINT_DYNAMIC_RANGE", "key": key, "status": status})

    for group in groups:
        schemes = sorted({r["scheme"] for r in rows if r["group"] == group})
        for channel in channels:
            if channel == "AWGN":
                continue
            significant = False
            max_margin = -1.0
            for scheme in schemes:
                for snr_tenth in range(10, 61, 5):
                    snr = str(snr_tenth / 10).rstrip("0").rstrip(".")
                    channel_row = by_point[(group, channel, scheme, snr)]
                    awgn_row = by_point[(group, "AWGN", scheme, snr)]
                    p_channel = float(channel_row["FER"])
                    p_awgn = float(awgn_row["FER"])
                    bound = wilson_half_width(int(channel_row["frameErrors"]), int(channel_row["frames"]))
                    bound += wilson_half_width(int(awgn_row["frameErrors"]), int(awgn_row["frames"]))
                    margin = abs(p_channel - p_awgn) - bound
                    max_margin = max(max_margin, margin)
                    significant = significant or margin > 0.0
            status = "PASS" if significant else "FAIL_AWGN_INDISTINGUISHABLE"
            if not significant:
                failures.append({"type": status, "key": (group, channel)})
            checks.append({"check": "DISTINGUISHABLE_FROM_AWGN", "key": (group, channel),
                           "status": status, "maxWilsonMargin": max_margin})

    report = {
        "schemaVersion": "s5.grid_gate_report.v1",
        "schemePoints": len(rows),
        "totalSchemeFrames": sum(int(r["frames"]) for r in rows),
        "nanInfCount": sum(not all(math.isfinite(float(r[k])) for k in ("BER", "FER", "avgIterations", "avgDecodeUs")) for r in rows),
        "checks": checks,
        "advisories": advisories,
        "failures": failures,
        "gate": "PASS_S5_SMOKE" if not failures else "FAIL_S5_SMOKE"
    }
    pathlib.Path(sys.argv[2]).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["gate"])
    for item in advisories:
        print("ADVISORY", item)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
