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


def select(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    values = defaultdict(lambda: [[], []])
    for row in rows:
        if row["comparisonRole"] == "BASELINE" or float(row["burstRatioRequested"]) not in (0.05, 0.10):
            continue
        snr = float(row["EsN0Db"])
        values[snr][0].append(float(row["FER"]))
        values[snr][1].append(float(row["BER"]))
    means = {snr: (sum(v[0]) / len(v[0]), sum(v[1]) / len(v[1])) for snr, v in values.items()}
    snrs = sorted(means)
    candidates = []
    for left, right in zip(snrs, snrs[1:]):
        fer_drop = max(0.0, means[left][0] - means[right][0])
        ber_drop = max(0.0, means[left][1] - means[right][1])
        candidates.append((fer_drop + ber_drop, right, left, fer_drop, ber_drop))
    score, waterfall, left, fer_drop, ber_drop = max(candidates, key=lambda item: (item[0], -item[1]))
    return {
        "lowEsN0Db": snrs[0],
        "waterfallEsN0Db": waterfall,
        "highEsN0Db": snrs[-1],
        "waterfallLeftEsN0Db": left,
        "waterfallScore": score,
        "ferDrop": fer_drop,
        "berDrop": ber_drop,
        "selectionPopulation": "non-baseline configurations, burst ratios 5% and 10%, six positions",
    }


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stage12_all_start_scan" / "selected_workpoints.json"
    result = {
        "status": "FROZEN",
        "method": "formal endpoints plus maximum adjacent mean FER+BER decrease",
        "sources": {scheme: str(path.resolve()) for scheme, path in SOURCES.items()},
        "schemes": {scheme: select(path) for scheme, path in SOURCES.items()},
        "mergeStatus": "NOT_MERGED",
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
