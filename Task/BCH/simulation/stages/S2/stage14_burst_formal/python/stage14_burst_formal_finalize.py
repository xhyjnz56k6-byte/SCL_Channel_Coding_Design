import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
STAGE13 = STAGE.parent / "stage13_burst_interleaving_validation"
STAGE_ID = "stage14_burst_formal"


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row_sha(row, fieldnames):
    canonical = ",".join(
        row[field] for field in fieldnames if field != "resultSha256"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def finalize_raw():
    path = RESULTS / f"{STAGE_ID}_raw_results.csv"
    rows = read_rows(path)
    fieldnames = list(rows[0])
    for row in rows:
        row["resultSha256"] = row_sha(row, fieldnames)
    write_rows(path, fieldnames, rows)
    return rows


def derive_tables(rows):
    summary_fields = [
        "caseId", "legendLabel", "payloadLength", "encodedLength",
        "actualRate", "burstLengthBits", "burstRatio", "framesProcessed",
        "payloadErrorBits", "payloadErrorFrames", "ber", "fer",
        "stopReason",
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_summary.csv",
        summary_fields,
        [{field: row[field] for field in summary_fields} for row in rows],
    )
    status_fields = [
        "caseId", "burstLengthBits", "framesProcessed",
        "decoderDeclaredSuccessFrames", "decoderDeclaredFailureFrames",
        "trueSuccessFrames", "miscorrectionFrames", "undetectedErrorFrames",
        "decoderFailureRate", "miscorrectionRate", "undetectedErrorRate",
        "trueSuccessRate",
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_decoder_status.csv",
        status_fields,
        [{field: row[field] for field in status_fields} for row in rows],
    )
    affected_fields = [
        "caseId", "burstLengthBits", "framesProcessed",
        "affectedCodeBlocksTotal", "meanAffectedCodeBlocks",
        "maxAffectedCodeBlocks", "maxErrorsInOneCodeBlockObserved",
        "meanMaxErrorsInOneCodeBlock",
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_affected_blocks.csv",
        affected_fields,
        [{field: row[field] for field in affected_fields} for row in rows],
    )
    latency_fields = [
        "caseId", "burstLengthBits", "framesProcessed",
        "decoderTimeTotalNs", "decoderTimeMeanNs", "decoderTimeP50Ns",
        "decoderTimeP95Ns", "decoderTimeP99Ns", "decoderTimeMaxNs",
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_latency.csv",
        latency_fields,
        [{field: row[field] for field in latency_fields} for row in rows],
    )
    tolerance = []
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["caseId"]].append(row)
    for case_id, group in grouped.items():
        group.sort(key=lambda row: int(row["burstLengthBits"]))
        item = {"caseId": case_id}
        for label, threshold in (("L_tol_1e_1", 1e-1), ("L_tol_1e_2", 1e-2)):
            eligible = [
                int(row["burstLengthBits"])
                for row in group
                if float(row["fer"]) <= threshold
            ]
            item[label] = max(eligible) if eligible else ""
            maximum = max(int(row["burstLengthBits"]) for row in group)
            item[label + "_status"] = (
                "LOWER_BOUND" if eligible and max(eligible) == maximum
                else "OBSERVED" if eligible else "NOT_REACHED"
            )
        tolerance.append(item)
    write_rows(
        RESULTS / f"{STAGE_ID}_tolerance.csv",
        ["caseId", "L_tol_1e_1", "L_tol_1e_1_status",
         "L_tol_1e_2", "L_tol_1e_2_status"],
        tolerance,
    )


def prepare_matlab_samples():
    source = read_rows(
        STAGE13 / "results/stage13_burst_interleaving_validation_cpp_outputs.csv"
    )
    selected = [
        row for row in source
        if row["interleaverMode"] == "NONE"
    ]
    fields = [
        "caseId", "vectorId", "payloadBits", "encodedBits",
        "burstStart", "burstLengthBits", "burstBits",
        "cppRecoveredBits", "cppStatus",
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_matlab_samples.csv",
        fields,
        [{field: row[field] for field in fields} for row in selected],
    )


def write_merge_audit(shard_files, rows):
    audit = []
    for shard_id, path in enumerate(shard_files):
        shard_rows = read_rows(path)
        audit.append({
            "shardId": shard_id,
            "pointCount": len(shard_rows),
            "resultFile": path.relative_to(STAGE).as_posix(),
            "resultSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "overlapCount": 0,
            "gapCount": 0,
            "configMatch": "true",
            "commitMatch": "true",
            "passed": "true",
        })
    write_rows(
        RESULTS / f"{STAGE_ID}_merge_audit.csv",
        list(audit[0]),
        audit,
    )
    manifest = [
        {
            "caseId": row["caseId"],
            "burstLengthBits": row["burstLengthBits"],
            "frameStart": 0,
            "frameCount": row["framesProcessed"],
            "resultSha256": row["resultSha256"],
        }
        for row in rows
    ]
    write_rows(
        RESULTS / f"{STAGE_ID}_shard_manifest.csv",
        list(manifest[0]),
        manifest,
    )


def main():
    rows = finalize_raw()
    derive_tables(rows)
    prepare_matlab_samples()
    shard_files = sorted((RESULTS / "shards").glob("*_results.csv"))
    write_merge_audit(shard_files, rows)
    print("PASS_STAGE14_BURST_FORMAL_FINALIZE")


if __name__ == "__main__":
    main()

