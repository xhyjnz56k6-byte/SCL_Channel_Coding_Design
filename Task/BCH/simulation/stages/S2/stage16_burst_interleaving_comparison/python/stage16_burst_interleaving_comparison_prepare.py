import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
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


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def representative_lengths(stage14):
    selections = []
    result = {}
    for payload in (200, 300):
        subset = [
            row for row in stage14 if int(row["payloadLength"]) == payload
        ]
        lengths = sorted({int(row["burstLengthBits"]) for row in subset})
        chosen = next(
            (
                length for length in lengths
                if any(
                    0.1 <= float(row["fer"]) <= 0.8
                    for row in subset
                    if int(row["burstLengthBits"]) == length
                )
            ),
            None,
        )
        if chosen is None:
            chosen = min(
                lengths,
                key=lambda length: (
                    abs(
                        sum(
                            float(row["fer"]) for row in subset
                            if int(row["burstLengthBits"]) == length
                        ) / 4.0 - 0.3
                    ),
                    length,
                ),
            )
            rule = "CLOSEST_PAYLOAD_MEAN_TO_FER_0.3"
        else:
            rule = "SMALLEST_UNIFIED_L_WITH_ANY_NONE_FER_IN_0.1_TO_0.8"
        values = {
            row["caseId"]: row["fer"] for row in subset
            if int(row["burstLengthBits"]) == chosen
        }
        result[payload] = chosen
        selections.append({
            "payloadLength": payload,
            "representativeBurstLengthBits": chosen,
            "selectionRule": rule,
            "sameLengthForAllFourCases": "true",
            "caseFerJson": json.dumps(values, ensure_ascii=False, sort_keys=True),
            "sourceFile": "stage14_burst_formal_raw_results.csv",
        })
    return result, selections


def best_depths(depth_rows, selected_modes):
    output = []
    result = {}
    for case_id in CASES:
        mode = selected_modes[case_id]
        candidates = []
        for depth in (4, 8, 16):
            group = [
                row for row in depth_rows
                if row["caseId"] == case_id
                and row["interleaverMode"] == mode
                and int(row["interleaverDepth"]) == depth
            ]
            geomean = math.exp(sum(
                math.log(max(
                    float(row["fer"]),
                    0.5 / int(row["framesProcessed"]),
                ))
                for row in group
            ) / len(group))
            miscorrection = sum(
                float(row["miscorrectionRate"]) for row in group
            ) / len(group)
            tolerated = [
                int(row["burstLengthBits"]) for row in group
                if float(row["fer"]) <= 0.1
            ]
            tolerance = max(tolerated) if tolerated else -1
            latency = sum(
                float(row["interleaverTimeMeanNs"])
                + float(row["deinterleaverTimeMeanNs"])
                for row in group
            ) / len(group)
            candidates.append(
                (geomean, miscorrection, -tolerance, latency, depth)
            )
        best = min(candidates)
        result[case_id] = best[4]
        output.append({
            "caseId": case_id,
            "bestInterleaverMode": mode,
            "bestInterleaverDepth": best[4],
            "ferGeometricMean": format(best[0], ".17g"),
            "miscorrectionMean": format(best[1], ".17g"),
            "toleranceL1e1": -best[2],
            "meanInterleaverOverheadNs": format(best[3], ".17g"),
            "selectionRule": (
                "FER_GEOMEAN,MISCORRECTION,TOLERANCE,LATENCY,DEPTH"
            ),
            "sourceFile": "stage15_interleaving_formal_depth_results.csv",
        })
    return result, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--forced-representative-burst-length", type=int)
    args = parser.parse_args()
    results = args.results_dir
    config = json.loads(
        (STAGE / f"configs/{STAGE_ID}_config.json").read_text(encoding="utf-8")
    )
    stage14 = read(STAGE14 / "results/stage14_burst_formal_raw_results.csv")
    stage15_selection = read(
        STAGE15
        / "results/stage15_interleaving_formal_best_interleaver_selection.csv"
    )
    selected_modes = {
        row["caseId"]: row["bestInterleaverMode"]
        for row in stage15_selection
    }
    depth_rows = read(
        STAGE15 / "results/stage15_interleaving_formal_depth_results.csv"
    )
    representative, representative_rows = representative_lengths(stage14)
    if args.forced_representative_burst_length is not None:
        require_length = args.forced_representative_burst_length
        if require_length <= 0:
            raise SystemExit("forced representative burst length must be positive")
        representative = {200: require_length, 300: require_length}
        for row in representative_rows:
            row["representativeBurstLengthBits"] = require_length
            row["selectionRule"] = "USER_FROZEN_UNIFIED_L"
    depths, depth_selection_rows = best_depths(depth_rows, selected_modes)
    write(
        results / f"{STAGE_ID}_representative_burst_selection.csv",
        representative_rows,
    )
    write(
        results / f"{STAGE_ID}_best_depth_selection.csv",
        depth_selection_rows,
    )
    sha_rows = read(
        STAGE13
        / "results/stage13_burst_interleaving_validation_permutation_sha256.csv"
    )
    sha = {
        (row["caseId"], row["interleaverMode"], int(row["interleaverDepth"])):
        row["permutationSha256"]
        for row in sha_rows
    }
    lengths = {
        row["caseId"]: (
            int(row["payloadLength"]), int(row["encodedLength"]),
            float(row["actualRate"])
        )
        for row in stage14
    }
    points = []
    for case_id in CASES:
        payload, _, rate = lengths[case_id]
        lrep = representative[payload]
        configurations = [
            ("NONE_L0", "NONE", 1, 0, 0),
            ("NONE_LREP", "NONE", 1, 1, lrep),
            (
                "BEST_LREP", selected_modes[case_id], depths[case_id],
                1, lrep,
            ),
        ]
        for configuration, mode, depth, burst_index, burst_length in configurations:
            for snr_index in range(config["snr"]["pointCount"]):
                target = (
                    config["snr"]["minimumDb"]
                    + config["snr"]["stepDb"] * snr_index
                )
                derived = target - 10.0 * math.log10(rate)
                points.append({
                    "caseId": case_id,
                    "configurationId": configuration,
                    "interleaverMode": mode,
                    "interleaverDepth": depth,
                    "burstLengthIndex": burst_index,
                    "burstLengthBits": burst_length,
                    "snrIndex": snr_index,
                    "targetSnrDb": format(target, ".17g"),
                    "derivedEbN0Db": format(derived, ".17g"),
                    "permutationSha256": sha[(case_id, mode, depth)],
                })
    write(results / f"{STAGE_ID}_points.csv", points)
    print("PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_PREPARE")


if __name__ == "__main__":
    main()
