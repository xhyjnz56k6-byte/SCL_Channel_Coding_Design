import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
STAGE14 = STAGE.parent / "stage14_burst_formal"
STAGE15 = STAGE.parent / "stage15_interleaving_formal"
RESULTS = STAGE / "results"
STAGE_ID = "stage16_burst_interleaving_comparison"
CASES = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row_hash(row, fields):
    text = ",".join(row.get(field, "") for field in fields if field != "resultSha256")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_shards():
    files = sorted(
        (RESULTS / "shards").glob(f"{STAGE_ID}_shard_*_results.csv")
    )
    merged = []
    fields = None
    audit = []
    for shard_id, path in enumerate(files):
        rows = read(path)
        if fields is None:
            fields = list(rows[0])
        elif list(rows[0]) != fields:
            raise SystemExit("Stage16 shard headers differ")
        merged.extend(rows)
        audit.append({
            "shardId": shard_id,
            "rowCount": len(rows),
            "resultFile": path.relative_to(STAGE).as_posix(),
            "resultSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "passed": "true",
        })
    merged.sort(key=lambda row: (
        CASES.index(row["caseId"]),
        ["NONE_L0", "NONE_LREP", "BEST_LREP"].index(row["configurationId"]),
        int(row["snrIndex"]),
    ))
    for row in merged:
        row["resultSha256"] = row_hash(row, fields)
    write(RESULTS / f"{STAGE_ID}_raw_results.csv", merged, fields)
    write(RESULTS / f"{STAGE_ID}_merge_audit.csv", audit)
    return merged


def threshold(group, target):
    ordered = sorted(group, key=lambda row: float(row["targetSnrDb"]))
    exact = [
        float(row["targetSnrDb"]) for row in ordered
        if math.isclose(float(row["fer"]), target, rel_tol=1e-12, abs_tol=1e-15)
    ]
    if exact:
        return min(exact), "EXACT"
    for left, right in zip(ordered, ordered[1:]):
        f1, f2 = float(left["fer"]), float(right["fer"])
        if f1 > target > f2 and f1 > 0 and f2 > 0:
            x1, x2 = float(left["targetSnrDb"]), float(right["targetSnrDb"])
            y1, y2, yt = math.log10(f1), math.log10(f2), math.log10(target)
            return x1 + (yt - y1) * (x2 - x1) / (y2 - y1), "INTERPOLATED"
    positive = [float(row["fer"]) for row in ordered if float(row["fer"]) > 0]
    if positive and min(positive) > target:
        return None, "NOT_REACHED"
    if float(ordered[0]["fer"]) < target:
        return None, "BELOW_RANGE"
    return None, "ABOVE_RANGE"


def summaries(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["caseId"], row["configurationId"])].append(row)
    targets = []
    for (case_id, configuration), group in grouped.items():
        for target in (0.1, 0.01):
            value, status = threshold(group, target)
            targets.append({
                "caseId": case_id,
                "configurationId": configuration,
                "targetFer": format(target, ".17g"),
                "targetSnrDb": "" if value is None else format(value, ".17g"),
                "status": status,
                "interpolationDomain": (
                    "LOG10_FER_WITHIN_OBSERVED_BRACKET"
                    if status == "INTERPOLATED" else "NONE"
                ),
                "extrapolated": "false",
            })
    write(RESULTS / f"{STAGE_ID}_target_fer_snr.csv", targets)
    lookup = {
        (row["caseId"], row["configurationId"], row["targetFer"]): row
        for row in targets
    }
    penalties = []
    for case_id in CASES:
        for target in ("0.10000000000000001", "0.01"):
            baseline = lookup[(case_id, "NONE_L0", target)]
            burst = lookup[(case_id, "NONE_LREP", target)]
            best = lookup[(case_id, "BEST_LREP", target)]
            for comparison, left, right in (
                ("BURST_PENALTY", burst, baseline),
                ("INTERLEAVER_RECOVERY", burst, best),
            ):
                valid = left["targetSnrDb"] and right["targetSnrDb"]
                penalties.append({
                    "caseId": case_id,
                    "targetFer": target,
                    "comparison": comparison,
                    "snrDifferenceDb": (
                        format(
                            float(left["targetSnrDb"])
                            - float(right["targetSnrDb"]), ".17g"
                        ) if valid else ""
                    ),
                    "status": "AVAILABLE" if valid else "NOT_COMPARABLE",
                    "leftStatus": left["status"],
                    "rightStatus": right["status"],
                })
    write(RESULTS / f"{STAGE_ID}_snr_penalty.csv", penalties)

    stage14 = read(STAGE14 / "results/stage14_burst_formal_tolerance.csv")
    stage15_selection = read(
        STAGE15
        / "results/stage15_interleaving_formal_best_interleaver_selection.csv"
    )
    depth_selection = read(RESULTS / f"{STAGE_ID}_best_depth_selection.csv")
    depth_lookup = {row["caseId"]: row for row in depth_selection}
    selection_lookup = {row["caseId"]: row for row in stage15_selection}
    tolerance = []
    recommendations = []
    for row in stage14:
        case_id = row["caseId"]
        tolerance.append({
            "caseId": case_id,
            "noneLtol1e1": row["L_tol_1e_1"],
            "noneLtol1e2": row["L_tol_1e_2"],
            "noneLtol1e1Status": row["L_tol_1e_1_status"],
            "noneLtol1e2Status": row["L_tol_1e_2_status"],
            "bestInterleaverMode": selection_lookup[case_id]["bestInterleaverMode"],
            "bestInterleaverDepth": depth_lookup[case_id]["bestInterleaverDepth"],
            "sourceStages": "stage14_burst_formal|stage15_interleaving_formal",
        })
        recovery = next(
            (
                item for item in penalties
                if item["caseId"] == case_id
                and item["targetFer"] == "0.10000000000000001"
                and item["comparison"] == "INTERLEAVER_RECOVERY"
            ),
            None,
        )
        recommendations.append({
            "caseId": case_id,
            "payloadLength": 200 if case_id.startswith("K200") else 300,
            "recommendedInterleaverMode":
                selection_lookup[case_id]["bestInterleaverMode"],
            "recommendedDepth": depth_lookup[case_id]["bestInterleaverDepth"],
            "awgnBurstFer1e1RecoveryDb": (
                recovery["snrDifferenceDb"] if recovery else ""
            ),
            "awgnBurstStatus": recovery["status"] if recovery else "NOT_COMPARABLE",
            "scope": "BURST_AND_AWGN_PLUS_BURST_ONLY",
        })
    write(RESULTS / f"{STAGE_ID}_tolerance_summary.csv", tolerance)
    write(RESULTS / f"{STAGE_ID}_recommendation_matrix.csv", recommendations)


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    rows = merge_shards()
    summaries(rows)
    print("PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_FINALIZE")


if __name__ == "__main__":
    main()
