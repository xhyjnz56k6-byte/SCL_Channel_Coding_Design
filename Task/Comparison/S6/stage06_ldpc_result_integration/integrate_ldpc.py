#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCE = ROOT / "Task" / "LDPC" / "block" / "stages" / "stage23_s4_final_reintegration" / "results" / "s4_revised_formal_point_results.csv"
OUTPUT = ROOT / "Task" / "Comparison" / "S6" / "results" / "ldpc"


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not SOURCE.exists():
        raise RuntimeError("LDPC Formal source is missing")
    source_hash = sha256(SOURCE)
    all_rows = read_csv(SOURCE)
    rows = [row for row in all_rows if row["caseId"] == "LDPC_BG2_K300_N560"]
    if len(rows) != 62:
        raise RuntimeError(f"N560 row count {len(rows)} != 62")
    output_rows = []
    finite_fields = (
        "BER", "FER", "avgIterations", "medianIterations", "p95Iterations", "maxUsedIterations",
        "earlyStopRate", "maxIterationRate", "avgDecodeTimeUs", "medianDecodeTimeUs",
        "p95DecodeTimeUs", "maxDecodeTimeUs", "checkNodeUpdates", "variableNodeUpdates",
        "messageUpdates", "tanhOperations", "atanhOperations", "atanhClampCount", "absOperations",
        "comparisonOperations", "min1Min2Updates", "signOperations", "alphaMultiplications",
        "decoderMemoryBytes")
    for row in rows:
        if row["maxIterations"] != "32" or row["earlyStopPolicy"] != "SYNDROME_AFTER_FULL_ITERATION":
            raise RuntimeError("N560 iteration configuration mismatch")
        if any(not math.isfinite(float(row[field])) or float(row[field]) < 0 for field in finite_fields):
            raise RuntimeError(f"invalid N560 metric: {row['runId']}")
        algorithm = "BP" if row["algorithm"] == "DIRECT_LAYERED_SPA_BP" else "NMS"
        if algorithm == "NMS" and float(row["alpha"]) != 0.95:
            raise RuntimeError("N560 NMS alpha is not 0.95")
        output_rows.append({
            "caseId": "LDPC_BG2_K300_N560",
            "algorithm": algorithm,
            "decoder": row["algorithm"],
            "payloadBits": row["payloadLength"],
            "actualLength": row["actualLength"],
            "actualRate": row["actualRate"],
            "Zc": row["Zc"],
            "fillerBits": row["fillerLength"],
            "parityLength": row["parityLength"],
            "rankHp": row["rankHp"],
            "rateMatching": "false",
            "rateRecover": "false",
            "interleaving": "false",
            "maxIterations": row["maxIterations"],
            "earlyStopPolicy": row["earlyStopPolicy"],
            "alpha": row["alpha"],
            "esN0Db": row["esN0Db"],
            "ebN0Db": row["ebN0Db"],
            "frames": row["frames"],
            "bitErrors": row["bitErrors"],
            "frameErrors": row["frameErrors"],
            "BER": row["BER"],
            "FER": row["FER"],
            "avgIterations": row["avgIterations"],
            "medianIterations": row["medianIterations"],
            "p95Iterations": row["p95Iterations"],
            "maxIterationsUsed": row["maxUsedIterations"],
            "earlyStopRate": row["earlyStopRate"],
            "maxIterationRate": row["maxIterationRate"],
            "correctValid": row["correctValidFrames"],
            "wrongValid": row["wrongValidFrames"],
            "correctInvalid": row["correctInvalidFrames"],
            "wrongInvalid": row["wrongInvalidFrames"],
            "avgDecodeTimeUs": row["avgDecodeTimeUs"],
            "medianDecodeTimeUs": row["medianDecodeTimeUs"],
            "p95DecodeTimeUs": row["p95DecodeTimeUs"],
            "maxDecodeTimeUs": row["maxDecodeTimeUs"],
            "edgeMessageUpdates": row["messageUpdates"],
            "checkNodeUpdates": row["checkNodeUpdates"],
            "variableNodeUpdates": row["variableNodeUpdates"],
            "tanhCount": row["tanhOperations"],
            "atanhCount": row["atanhOperations"],
            "atanhClampCount": row["atanhClampCount"],
            "absCount": row["absOperations"],
            "comparisonCount": row["comparisonOperations"],
            "min1Min2Count": row["min1Min2Updates"],
            "signCount": row["signOperations"],
            "alphaScaleCount": row["alphaMultiplications"],
            "decoderMemoryBytes": row["decoderMemoryBytes"],
            "payloadHash": row["payloadHash"],
            "codewordHash": row["codewordHash"],
            "llrHash": row["llrHash"],
            "configHash": row["configHash"],
            "sourceRunId": row["runId"],
            "sourceFile": SOURCE.relative_to(ROOT).as_posix(),
            "sourceSha256": source_hash,
        })
    output_rows.sort(key=lambda row: (float(row["esN0Db"]), row["algorithm"]))
    by_snr = {}
    for row in output_rows:
        by_snr.setdefault(row["esN0Db"], []).append(row)
    paired = all(len(pair) == 2 and len({item["payloadHash"] for item in pair}) == 1
                 and len({item["codewordHash"] for item in pair}) == 1
                 and len({item["llrHash"] for item in pair}) == 1 for pair in by_snr.values())
    if len(by_snr) != 31 or not paired:
        raise RuntimeError("N560 BP/NMS pairing hash mismatch")
    write_csv(OUTPUT / "ldpc_n560_integrated_results.csv", output_rows)
    inventory = [{
        "sourceFile": SOURCE.relative_to(ROOT).as_posix(),
        "fileSizeBytes": SOURCE.stat().st_size,
        "sha256": source_hash,
        "sourceRows": len(all_rows),
        "selectedRows": len(output_rows),
        "selection": "LDPC_BG2_K300_N560; BP/NMS; maxIter=32; NMS alpha=0.95",
    }]
    write_csv(OUTPUT / "ldpc_source_inventory.csv", inventory)
    summary = {
        "schemaVersion": "s6.ldpc.n560.integration.v1",
        "formalRerun": False,
        "selectedRows": len(output_rows),
        "pairedSnrPoints": len(by_snr),
        "sharedPayloadCodewordLlr": paired,
        "sharedEarlyStop": "SYNDROME_AFTER_FULL_ITERATION",
        "maxIterations": 32,
        "nmsAlpha": 0.95,
        "formalIterationComparisonsAvailable": [32],
        "notFormallyCompared": [10, 20, 30],
        "sourceSha256": source_hash,
        "gate": "PASS_LDPC_N560_RESULT_INTEGRATION",
    }
    (OUTPUT / "ldpc_integration_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summary["gate"], f"rows={len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
