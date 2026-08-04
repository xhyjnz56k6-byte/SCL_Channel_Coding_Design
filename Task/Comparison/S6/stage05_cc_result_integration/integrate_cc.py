#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCE = ROOT / "Task" / "CC" / "simulation" / "stages" / "S3" / "stage14_block_continuous_comparison" / "results" / "stage14_online_slot_formal_results_all_decisions.csv"
OUTPUT = ROOT / "Task" / "Comparison" / "S6" / "results" / "cc"


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


def finite(row, fields):
    return all(math.isfinite(float(row[field])) for field in fields)


def main():
    if not SOURCE.exists():
        raise RuntimeError("CC Formal source is missing")
    source_hash = sha256(SOURCE)
    source_rows = read_csv(SOURCE)
    selected = [row for row in source_rows if row["rateCase"] == "R12" and row["organization"] in {
        "A_BLOCK_300", "B_CONT_50x6", "C_CONT_100x3", "D_CONT_150x2"}]
    if len(selected) != 248:
        raise RuntimeError(f"CC frozen row count {len(selected)} != 248")
    output_rows = []
    for row in selected:
        is_block = row["organization"] == "A_BLOCK_300"
        is_hard = row["decisionMode"] == "Hard"
        if not is_block and (row["dtb"] != "70" or row["windowBits"] != "128" or row["slideBits"] != "25"):
            raise RuntimeError("slot row violates D70/W128/S25")
        if is_block and row["dtb"] != "306":
            raise RuntimeError("block row is not full traceback D=306")
        required = ("BER", "FER", "actualRate", "ACSCount", "tracebackOperations",
                    "totalMemoryBytes", "avgDecodeTimeUs", "p95DecodeTimeUs", "maxDecodeTimeUs")
        if not finite(row, required):
            raise RuntimeError(f"non-finite CC metric: {row['caseId']}")
        organization_mode = "BLOCK" if is_block else "SLOT"
        decision_label = "HARD" if is_hard else "FLOAT_SOFT"
        output_rows.append({
            "schemeId": f"{organization_mode}_{decision_label}" if is_block else f"{row['organization']}_{decision_label}",
            "organizationMode": organization_mode,
            "slotOrganization": "NOT_APPLICABLE" if is_block else row["organization"],
            "decisionInformation": "Hard" if is_hard else "Float Soft",
            "inputPrecision": "1 bit" if is_hard else "Float",
            "payloadBits": "300",
            "transmittedBits": row["transmittedBits"],
            "actualRate": row["actualRate"],
            "esN0Db": row["esN0Db"],
            "ebN0Db": row["ebN0Db"],
            "frames": row["frames"],
            "bitErrors": row["bitErrors"],
            "frameErrors": row["frameErrors"],
            "BER": row["BER"],
            "FER": row["FER"],
            "tracebackDepthD": row["dtb"],
            "windowLengthW": row["windowBits"],
            "slideStepS": row["slideBits"],
            "ACSCount": row["ACSCount"],
            "tracebackOperations": row["tracebackOperations"],
            "windowTriggerCount": row["windowTriggerCount"],
            "decoderMemoryBytes": row["totalMemoryBytes"],
            "avgCpuDecodeTimeUs": row["avgDecodeTimeUs"],
            "medianCpuDecodeTimeUs": row["medianDecodeTimeUs"],
            "p95CpuDecodeTimeUs": row["p95DecodeTimeUs"],
            "maxCpuDecodeTimeUs": row["maxDecodeTimeUs"],
            "firstOutputDelaySymbols": row["firstOutputDelaySymbols"],
            "avgDecisionDelaySymbols": row["avgDecisionDelaySymbols"],
            "medianDecisionDelaySymbols": row["medianDecisionDelaySymbols"],
            "p95DecisionDelaySymbols": row["p95DecisionDelaySymbols"],
            "maxDecisionDelaySymbols": row["maxDecisionDelaySymbols"],
            "timingSeparation": "CPU译码时间（微秒）与实时决策时延（符号）分列",
            "stopPolicyLimitation": "历史结果非严格pair-stop",
            "sourceFile": SOURCE.relative_to(ROOT).as_posix(),
            "sourceSha256": source_hash,
            "sourceCaseId": row["caseId"],
            "sourceNoiseId": row["sourceNoiseId"],
        })
    output_rows.sort(key=lambda row: (row["organizationMode"], row["schemeId"], float(row["esN0Db"])))
    write_csv(OUTPUT / "cc_integrated_results.csv", output_rows)
    inventory = [{
        "sourceFile": SOURCE.relative_to(ROOT).as_posix(),
        "fileSizeBytes": SOURCE.stat().st_size,
        "sha256": source_hash,
        "sourceRows": len(source_rows),
        "selectedRows": len(output_rows),
        "selection": "R12; A_BLOCK_300/B_CONT_50x6/C_CONT_100x3/D_CONT_150x2; Hard/Soft Float",
    }]
    write_csv(OUTPUT / "cc_source_inventory.csv", inventory)
    groups = {}
    for row in output_rows:
        groups[row["schemeId"]] = groups.get(row["schemeId"], 0) + 1
    expected = {
        "BLOCK_HARD", "BLOCK_FLOAT_SOFT",
        "B_CONT_50x6_HARD", "B_CONT_50x6_FLOAT_SOFT",
        "C_CONT_100x3_HARD", "C_CONT_100x3_FLOAT_SOFT",
        "D_CONT_150x2_HARD", "D_CONT_150x2_FLOAT_SOFT",
    }
    gate = set(groups) == expected and all(value == 31 for value in groups.values())
    summary = {
        "schemaVersion": "s6.cc.integration.v1",
        "formalRerun": False,
        "selectedRows": len(output_rows),
        "schemeRows": groups,
        "sourceSha256": source_hash,
        "inputPrecision": {"Hard": "1 bit", "Float Soft": "Float"},
        "limitations": ["非严格pair-stop", "CPU译码时间与实时决策时延不可混用", "Q4/Q6/Q8不是主Float Soft"],
        "gate": "PASS_CC_RESULT_INTEGRATION" if gate else "BLOCK_CC_RESULT_INTEGRATION",
    }
    (OUTPUT / "cc_integration_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not gate:
        raise RuntimeError(summary["gate"])
    print(summary["gate"], f"rows={len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
