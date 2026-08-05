import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "stage12_all_start_scan"
    output = root / "results" / "all_start_summary.csv"
    fields = ["scheme", "configurationId", "workpointRole", "EsN0Db", "burstRatioRequested", "meanFerAcrossStarts", "worstFer", "bestFer", "worstStart", "bestStart", "failureStartRatio", "boundaryStartFer", "tailRemainderFer", "startCount"]
    summaries = []
    for scheme in ("bch", "cc"):
        rows = list(csv.DictReader((root / "results" / scheme / "all_start_results.csv").open(encoding="utf-8")))
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row["scheme"], row["configurationId"], row["workpointRole"], row["EsN0Db"], row["burstRatioRequested"])].append(row)
        for key, group in sorted(grouped.items()):
            group.sort(key=lambda row: int(row["burstStart"]))
            fers = [float(row["FER"]) for row in group]
            worst = max(range(len(group)), key=lambda i: (fers[i], -int(group[i]["burstStart"])))
            best = min(range(len(group)), key=lambda i: (fers[i], int(group[i]["burstStart"])))
            summaries.append(dict(zip(fields[:5], key), meanFerAcrossStarts=sum(fers) / len(fers), worstFer=fers[worst], bestFer=fers[best], worstStart=group[worst]["burstStart"], bestStart=group[best]["burstStart"], failureStartRatio=sum(value > 0 for value in fers) / len(fers), boundaryStartFer=fers[0], tailRemainderFer=fers[-1], startCount=len(group)))
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(summaries)
    print(f"PASS_S7_STAGE12_ANALYSIS rows={len(summaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
