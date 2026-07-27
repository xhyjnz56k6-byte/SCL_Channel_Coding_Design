import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
STAGE14 = STAGE.parent / "stage14_burst_formal"
RESULTS = STAGE / "results"
STAGE_ID = "stage15_interleaving_formal"
CASE_ORDER = [
    "K200_S15", "K200_M255K207", "K200_M511K421", "K200_M511K385",
    "K300_S15", "K300_M255K207", "K300_M511K421", "K300_M511K385",
]
MODES = ["BLOCK", "ROW_COLUMN", "PSEUDORANDOM"]


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write(path, data, fields=None):
    if fields is None:
        fields = list(data[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def merge_shards(prefix, output):
    files = sorted((RESULTS / "shards").glob(f"{prefix}_shard_*_results.csv"))
    merged = []
    fields = None
    for path in files:
        data = rows(path)
        if data:
            if fields is None:
                fields = list(data[0])
            elif list(data[0]) != fields:
                raise SystemExit("Stage15 shard headers differ")
            merged.extend(data)
    merged.sort(key=lambda row: (
        CASE_ORDER.index(row["caseId"]),
        row["interleaverMode"],
        int(row["interleaverDepth"]),
        int(row["burstLengthBits"]),
    ))
    write(output, merged, fields)
    return merged, files


def identity_sha():
    data = rows(
        STAGE13 / "results/stage13_burst_interleaving_validation_permutation_sha256.csv"
    )
    return {
        row["caseId"]: row["permutationSha256"]
        for row in data
        if row["interleaverMode"] == "NONE"
    }


def none_row(source, template_fields, commit):
    result = {field: "" for field in template_fields}
    for field in template_fields:
        if field in source:
            result[field] = source[field]
    result.update({
        "stageId": STAGE_ID,
        "runId": "stage15_reused_stage14_none",
        "gitCommit": commit,
        "interleaverMode": "NONE",
        "interleaverDepth": "1",
        "interleaverRows": "0",
        "interleaverColumns": "0",
        "interleaverBlockCount": "0",
        "interleaverSeed": "0",
        "permutationFile": (
            "../stage13_burst_interleaving_validation/results/"
            "stage13_burst_interleaving_validation_permutations.csv"
        ),
        "permutationSha256": identity_sha()[source["caseId"]],
        "interleaverApplyTimeTotalNs": "0",
        "deinterleaverApplyTimeTotalNs": "0",
        "interleaverTimeMeanNs": "0",
        "deinterleaverTimeMeanNs": "0",
        "interleaverBufferBits": "0",
        "interleaverBufferBytes": "0",
        "interleaverStartupDelayBits": "0",
        "checkpointPath": source["checkpointPath"],
        "_reusedSourceGitCommit": source["gitCommit"],
        "resultSha256": "",
    })
    return result


def add_improvement(data, none_lookup):
    fields = [
        "deltaFer", "relativeFerReduction", "ferImprovementRatio",
        "ratioStatus", "L_tol_1e_1", "L_tol_1e_2", "toleranceStatus",
        "sourceStage", "sourceGitCommit", "reuseStatus",
    ]
    base_fields = [
        field for field in data[0] if not field.startswith("_")
    ]
    grouped = defaultdict(list)
    for row in data:
        grouped[(row["caseId"], row["interleaverMode"],
                 int(row["interleaverDepth"]))].append(row)
    tolerance = {}
    for key, group in grouped.items():
        lengths_01 = [
            int(row["burstLengthBits"]) for row in group
            if float(row["fer"]) <= 1e-1
        ]
        lengths_001 = [
            int(row["burstLengthBits"]) for row in group
            if float(row["fer"]) <= 1e-2
        ]
        maximum = max(int(row["burstLengthBits"]) for row in group)
        tolerance[key] = (
            max(lengths_01) if lengths_01 else "",
            max(lengths_001) if lengths_001 else "",
            "LOWER_BOUND" if lengths_01 and max(lengths_01) == maximum
            else "OBSERVED" if lengths_01 else "NOT_REACHED",
        )
    for row in data:
        none = none_lookup[(row["caseId"], int(row["burstLengthBits"]))]
        fer_none = float(none["fer"])
        fer_value = float(row["fer"])
        row["deltaFer"] = format(fer_none - fer_value, ".17g")
        row["relativeFerReduction"] = (
            format((fer_none - fer_value) / fer_none, ".17g")
            if fer_none > 0 else ""
        )
        if fer_value > 0:
            row["ferImprovementRatio"] = format(fer_none / fer_value, ".17g")
            row["ratioStatus"] = "EXACT"
        else:
            row["ferImprovementRatio"] = ""
            row["ratioStatus"] = "LOWER_BOUND_ONLY"
        key = (
            row["caseId"], row["interleaverMode"],
            int(row["interleaverDepth"]),
        )
        row["L_tol_1e_1"], row["L_tol_1e_2"], row["toleranceStatus"] = tolerance[key]
        if row["interleaverMode"] == "NONE":
            row["sourceStage"] = "stage14_burst_formal"
            row["sourceGitCommit"] = (
                row.pop("_reusedSourceGitCommit", "") or none["gitCommit"]
            )
            row["reuseStatus"] = "REUSED_STAGE14_CANONICAL"
        else:
            row["sourceStage"] = STAGE_ID
            row["sourceGitCommit"] = row["gitCommit"]
            row["reuseStatus"] = "SIMULATED_STAGE15"
    return base_fields + fields


def canonical_hash(row, fields):
    text = ",".join(
        str(row.get(field, "")) for field in fields if field != "resultSha256"
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def select_best(method_rows, priority):
    selections = []
    for case_id in CASE_ORDER:
        candidates = []
        for mode in MODES:
            group = [
                row for row in method_rows
                if row["caseId"] == case_id
                and row["interleaverMode"] == mode
            ]
            log_fer = sum(
                math.log(max(
                    float(row["fer"]),
                    0.5 / int(row["framesProcessed"]),
                ))
                for row in group
            ) / len(group)
            geometric = math.exp(log_fer)
            miscorr = sum(float(row["miscorrectionRate"]) for row in group) / len(group)
            tolerance = max(
                int(row["burstLengthBits"]) for row in group
                if float(row["fer"]) <= 0.1
            ) if any(float(row["fer"]) <= 0.1 for row in group) else -1
            latency = sum(
                float(row["interleaverTimeMeanNs"])
                + float(row["deinterleaverTimeMeanNs"])
                for row in group
            ) / len(group)
            candidates.append((
                geometric, miscorr, -tolerance, latency,
                priority.index(mode), mode, tolerance,
            ))
        candidates.sort()
        best = candidates[0]
        tied = len(candidates) > 1 and candidates[0][:4] == candidates[1][:4]
        selections.append({
            "caseId": case_id,
            "bestInterleaverMode": best[5],
            "methodDepth": 8,
            "ferGeometricMean": format(best[0], ".17g"),
            "miscorrectionMean": format(best[1], ".17g"),
            "toleranceL1e1": best[6],
            "meanInterleaverOverheadNs": format(best[3], ".17g"),
            "tieDetected": str(tied).lower(),
            "tieBreakPriority": "|".join(priority),
            "selectionRule": (
                "FER_GEOMEAN,MISCORRECTION,TOLERANCE,LATENCY,PRIORITY"
            ),
        })
    return selections


def select_phase(config, frozen, commit):
    method_new, shard_files = merge_shards(
        f"{STAGE_ID}_method",
        RESULTS / f"{STAGE_ID}_method_new_results.csv",
    )
    template = list(method_new[0])
    stage14 = rows(STAGE14 / "results/stage14_burst_formal_raw_results.csv")
    allowed = {
        payload: set(frozen["stage15MethodBurstLengthsByPayload"][str(payload)])
        for payload in (200, 300)
    }
    none = [
        none_row(row, template, commit) for row in stage14
        if int(row["burstLengthBits"]) in allowed[int(row["payloadLength"])]
    ]
    method = none + method_new
    none_lookup = {
        (row["caseId"], int(row["burstLengthBits"])): row for row in none
    }
    fields = add_improvement(method, none_lookup)
    for row in method:
        row["resultSha256"] = canonical_hash(row, fields)
    method.sort(key=lambda row: (
        CASE_ORDER.index(row["caseId"]),
        ["NONE", *MODES].index(row["interleaverMode"]),
        int(row["burstLengthBits"]),
    ))
    write(RESULTS / f"{STAGE_ID}_method_results.csv", method, fields)
    selections = select_best(method, config["bestModePriority"])
    write(
        RESULTS / f"{STAGE_ID}_best_interleaver_selection.csv",
        selections,
    )

    sha_rows = rows(
        STAGE13 / "results/stage13_burst_interleaving_validation_permutation_sha256.csv"
    )
    sha_lookup = {
        (row["caseId"], row["interleaverMode"], int(row["interleaverDepth"])):
            row["permutationSha256"]
        for row in sha_rows
    }
    selection_lookup = {
        row["caseId"]: row["bestInterleaverMode"] for row in selections
    }
    point_rows = []
    for case_id in CASE_ORDER:
        payload = 200 if case_id.startswith("K200") else 300
        mode = selection_lookup[case_id]
        for depth in (4, 16):
            for index, length in enumerate(
                frozen["stage15DepthBurstLengthsByPayload"][str(payload)]
            ):
                point_rows.append({
                    "caseId": case_id,
                    "interleaverMode": mode,
                    "interleaverDepth": depth,
                    "burstLengthIndex": index,
                    "burstLengthBits": length,
                    "permutationSha256": sha_lookup[(case_id, mode, depth)],
                })
    write(
        RESULTS / f"{STAGE_ID}_depth_points.csv",
        point_rows,
    )
    return shard_files


def final_phase(config, frozen, commit):
    method = rows(RESULTS / f"{STAGE_ID}_method_results.csv")
    depth_new, depth_shards = merge_shards(
        f"{STAGE_ID}_depth",
        RESULTS / f"{STAGE_ID}_depth_new_results.csv",
    )
    template = list(depth_new[0])
    stage14 = rows(STAGE14 / "results/stage14_burst_formal_raw_results.csv")
    selection = {
        row["caseId"]: row["bestInterleaverMode"]
        for row in rows(RESULTS / f"{STAGE_ID}_best_interleaver_selection.csv")
    }
    allowed = {
        payload: set(frozen["stage15DepthBurstLengthsByPayload"][str(payload)])
        for payload in (200, 300)
    }
    none = [
        none_row(row, template, commit) for row in stage14
        if int(row["burstLengthBits"]) in allowed[int(row["payloadLength"])]
    ]
    d8 = [
        dict(row) for row in method
        if row["interleaverMode"] == selection[row["caseId"]]
        and int(row["burstLengthBits"])
        in allowed[int(row["payloadLength"])]
    ]
    for row in d8:
        row["resultSha256"] = ""
        for field in template:
            row.setdefault(field, "")
    depth = none + d8 + depth_new
    none_lookup = {
        (row["caseId"], int(row["burstLengthBits"])): row for row in none
    }
    fields = add_improvement(depth, none_lookup)
    for row in depth:
        row["resultSha256"] = canonical_hash(row, fields)
    depth.sort(key=lambda row: (
        CASE_ORDER.index(row["caseId"]),
        int(row["interleaverDepth"]),
        int(row["burstLengthBits"]),
    ))
    write(RESULTS / f"{STAGE_ID}_depth_results.csv", depth, fields)

    depth_new_enriched = [
        row for row in depth
        if row["interleaverMode"] != "NONE"
        and int(row["interleaverDepth"]) in {4, 16}
    ]
    unique = list(method) + depth_new_enriched
    seen = set()
    unique_rows = []
    for row in unique:
        key = (
            row["caseId"], row["interleaverMode"],
            int(row["interleaverDepth"]), int(row["burstLengthBits"]),
        )
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    all_fields = list(unique_rows[0])
    write(RESULTS / f"{STAGE_ID}_raw_results.csv", unique_rows, all_fields)
    return depth_shards


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args()
    config = json.loads(
        (STAGE / f"configs/{STAGE_ID}_config.json").read_text(encoding="utf-8")
    )
    frozen = json.loads(
        (STAGE13 / "results/stage13_burst_interleaving_validation_frozen_parameters.json")
        .read_text(encoding="utf-8")
    )
    if args.select:
        select_phase(config, frozen, args.git_commit)
        print("PASS_STAGE15_INTERLEAVING_FORMAL_SELECTION")
    elif args.finalize:
        final_phase(config, frozen, args.git_commit)
        print("PASS_STAGE15_INTERLEAVING_FORMAL_FINALIZE")
    else:
        raise SystemExit("choose --select or --finalize")


if __name__ == "__main__":
    main()
