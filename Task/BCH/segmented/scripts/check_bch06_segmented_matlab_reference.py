#!/usr/bin/env python3
"""Strict field-by-field BCH-06 C++/MATLAB CSV checker."""
import argparse
import csv
import hashlib
import json
import pathlib
import sys

FILES = [
    ("encoder", "cpp_encoder_reference.csv", "matlab_encoder_reference.csv", 2048, "encoder_compare_summary.csv"),
    ("syndrome", "cpp_syndrome_reference.csv", "matlab_syndrome_reference.csv", 15, "syndrome_compare_summary.csv"),
    ("no_error_decode", "cpp_no_error_decode.csv", "matlab_no_error_decode.csv", 2048, "no_error_decode_compare_summary.csv"),
    ("single_error_decode", "cpp_single_error_decode.csv", "matlab_single_error_decode.csv", 30720, "single_error_decode_compare_summary.csv"),
    ("segmented_noiseless", "cpp_segmented_noiseless_detail.csv", "matlab_segmented_noiseless_detail.csv", 208, "segmented_recovery_compare_summary.csv"),
    ("segmented_single_error", "cpp_segmented_single_error_detail.csv", "matlab_segmented_single_error_detail.csv", 705, "single_error_compare_summary.csv"),
    ("multi_block_single_error", "cpp_multi_block_single_error_detail.csv", "matlab_multi_block_single_error_detail.csv", 8, "multi_block_single_error_compare_summary.csv"),
    ("same_block_double_error", "cpp_same_block_double_error_detail.csv", "matlab_same_block_double_error_detail.csv", 12, "double_error_compare_summary.csv"),
    ("filler_boundary", "cpp_filler_boundary_detail.csv", "matlab_filler_boundary_detail.csv", 30, "filler_boundary_compare_summary.csv"),
    ("failure_status_retention", "cpp_failure_status_retention_detail.csv", "matlab_failure_status_retention_detail.csv", 4, "failure_status_compare_summary.csv"),
    ("frame_pool", "cpp_frame_pool_audit.csv", "matlab_frame_pool_audit.csv", 200, "frame_pool_compare_summary.csv"),
    ("fixed_multi_error", "cpp_fixed_multi_error_detail.csv", "matlab_fixed_multi_error_detail.csv", 96, "fixed_multi_error_compare_summary.csv"),
]

BOOL_FIELDS = {"lookupHit", "payloadRecovered", "pass", "codewordRecovered", "blockInformationWrong",
               "originalPayloadWrong", "fillerOnlyInformationMismatch", "miscorrection",
               "reportedCorrectly", "recoveredPaddedMessagePreserved"}
STATUS_FIELDS = {"status", "reportedStatus"}
POSITION_FIELDS = {"errorPosition", "correctedPosition", "globalPosition", "localPosition", "blockIndex",
                   "lastBlockIndex", "frameIndex", "messageIndex", "payloadLength", "encodedLength",
                   "errorCount", "correctedBlocks"}

def read_csv(path: pathlib.Path):
    if not path.exists():
        raise ValueError(f"missing file: {path}")
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise ValueError(f"NUL byte: {path}")
    for b in raw:
        if b < 32 and b not in (9, 10, 13):
            raise ValueError(f"control byte {b}: {path}")
        if b > 126:
            raise ValueError(f"non-ASCII byte {b}: {path}")
    text = raw.decode("ascii")
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows, hashlib.sha256(raw).hexdigest(), len(raw)

def expected_case_lengths(row):
    case_name = row.get("caseName", "")
    if case_name == "BCH-S200":
        return {"payload": 200, "padded": 209, "encoded": 285}
    if case_name == "BCH-S300":
        return {"payload": 300, "padded": 308, "encoded": 420}
    return None

def validate_bit_length(label, row, key, value, index):
    if not value:
        return
    fixed_lengths = {
        "messageBits": 11, "parityBits": 4, "codewordBits": 15,
        "syndromeBits": 4, "syndromeBefore": 4, "syndromeAfter": 4,
        "originalCodeword": 15, "receivedCodeword": 15,
        "correctedCodeword": 15, "decodedMessage": 11,
        "decodedBlockMessage": 11,
    }
    expected = fixed_lengths.get(key)
    if label in {"no_error_decode", "single_error_decode", "fixed_multi_error"} and key == "receivedBits":
        expected = 15
    lengths = expected_case_lengths(row)
    if lengths:
        if key in {"payloadBits", "recoveredPayload"}:
            expected = lengths["payload"]
        elif key in {"paddedMessageBits", "recoveredPaddedMessage", "expectedPaddedMessage"}:
            expected = lengths["padded"]
        elif key in {"encodedBits", "originalEncodedBits", "receivedBits"}:
            expected = lengths["encoded"]
    if expected is not None and len(value) != expected:
        raise ValueError(
            f"bad bit length field {key} row {index}: expected {expected}, got {len(value)}"
        )

def validate_scalar_fields(label, rows):
    statuses = {"NO_ERROR", "CORRECTED_SINGLE_ERROR", "POST_CHECK_FAILED", "UNRECOGNIZED_SYNDROME"}
    for index, row in enumerate(rows):
        for key, value in row.items():
            if key.endswith("Bits") or key in {"messageBits", "payloadBits", "receivedBits", "codewordBits",
                                               "parityBits", "syndromeBits", "syndromeBefore", "syndromeAfter",
                                               "originalCodeword", "receivedCodeword", "correctedCodeword",
                                               "decodedMessage", "decodedBlockMessage", "decodedBlockMessage",
                                               "recoveredPayload", "recoveredPaddedMessage", "expectedPaddedMessage",
                                               "paddedMessageBits", "encodedBits", "originalEncodedBits"}:
                if value and any(ch not in "01" for ch in value):
                    raise ValueError(f"bad bit string field {key} row {index}")
                validate_bit_length(label, row, key, value, index)
            if key in BOOL_FIELDS and value not in {"true", "false"}:
                raise ValueError(f"bad bool field {key} row {index}: {value}")
            if key in STATUS_FIELDS and value not in statuses:
                raise ValueError(f"bad status field {key} row {index}: {value}")
            if key in POSITION_FIELDS and value and value != "-1":
                int(value)

def compare_rows(label, cpp_rows, matlab_rows, expected_count):
    if expected_count is not None and (len(cpp_rows) != expected_count or len(matlab_rows) != expected_count):
        return {
            "name": label, "rowMismatchCount": abs(len(cpp_rows) - len(matlab_rows)) or 1,
            "fieldMismatchCount": 0, "firstMismatchRow": "row_count", "firstMismatchField": "row_count",
            "cppValue": str(len(cpp_rows)), "matlabValue": str(len(matlab_rows)), "fieldMismatches": {}
        }
    if len(cpp_rows) != len(matlab_rows):
        return {
            "name": label, "rowMismatchCount": abs(len(cpp_rows) - len(matlab_rows)),
            "fieldMismatchCount": 0, "firstMismatchRow": "row_count", "firstMismatchField": "row_count",
            "cppValue": str(len(cpp_rows)), "matlabValue": str(len(matlab_rows)), "fieldMismatches": {}
        }
    headers = list(cpp_rows[0].keys())
    if headers != list(matlab_rows[0].keys()):
        return {
            "name": label, "rowMismatchCount": 0, "fieldMismatchCount": 1,
            "firstMismatchRow": "header", "firstMismatchField": "header",
            "cppValue": "|".join(headers), "matlabValue": "|".join(matlab_rows[0].keys()), "fieldMismatches": {}
        }
    row_mismatch = 0
    field_mismatch = 0
    first_row = ""
    first_field = ""
    cpp_value = ""
    matlab_value = ""
    field_counts = {h: 0 for h in headers}
    for index, (a, b) in enumerate(zip(cpp_rows, matlab_rows)):
        row_diff = False
        for field in headers:
            if a[field] != b[field]:
                row_diff = True
                field_mismatch += 1
                field_counts[field] += 1
                if not first_field:
                    first_row = str(index)
                    first_field = field
                    cpp_value = a[field]
                    matlab_value = b[field]
        if row_diff:
            row_mismatch += 1
    return {
        "name": label,
        "rowMismatchCount": row_mismatch,
        "fieldMismatchCount": field_mismatch,
        "firstMismatchRow": first_row,
        "firstMismatchField": first_field,
        "cppValue": cpp_value,
        "matlabValue": matlab_value,
        "fieldMismatches": {k: v for k, v in field_counts.items() if v},
    }

def load_metrics(path):
    rows = list(csv.reader(path.open(encoding="ascii")))
    if rows[0] != ["metric", "value"]:
        raise ValueError("bad MATLAB summary header")
    return {k: int(v) for k, v in rows[1:]}

def validate_config(path):
    expected = {
        "code": "BCH(15,11,1)",
        "generatorPolynomial": "10011",
        "bitOrder": "leftmost_highest_degree",
        "S200": "200/19/9/285",
        "S300": "300/28/8/420",
        "fixedMultiErrorExpectedCount": "96",
    }
    rows = list(csv.reader(path.open(encoding="ascii")))
    if not rows or rows[0] != ["key", "value"]:
        raise ValueError(f"bad config header: {path}")
    values = {key: value for key, value in rows[1:]}
    if values != expected:
        raise ValueError(f"BCH-06 config mismatch: {path}")
    return values

def write_summary_csv(path, item):
    with path.open("w", newline="", encoding="ascii") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "cppRows", "matlabRows", "rowMismatchCount", "fieldMismatchCount",
                         "firstMismatchRow", "firstMismatchField", "cppValue", "matlabValue",
                         "cppSha256", "matlabSha256", "cppBytes", "matlabBytes"])
        writer.writerow([item["name"], item["cppRows"], item["matlabRows"], item["rowMismatchCount"],
                         item["fieldMismatchCount"], item["firstMismatchRow"], item["firstMismatchField"],
                         item["cppValue"], item["matlabValue"], item["cppSha256"], item["matlabSha256"],
                         item["cppBytes"], item["matlabBytes"]])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpp-dir", required=True)
    ap.add_argument("--matlab-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--config-path", required=True)
    args = ap.parse_args()
    cpp = pathlib.Path(args.cpp_dir)
    mat = pathlib.Path(args.matlab_dir)
    out = pathlib.Path(args.output_dir)
    config = validate_config(pathlib.Path(args.config_path))
    out.mkdir(parents=True, exist_ok=True)
    result = {"files": [], "singleBlockMismatchTotal": 0, "segmentedMismatchTotal": 0, "allMismatchTotal": 0}
    for label, cpp_name, matlab_name, count, summary_name in FILES:
        cpp_rows, cpp_sha, cpp_size = read_csv(cpp / cpp_name)
        matlab_rows, matlab_sha, matlab_size = read_csv(mat / matlab_name)
        validate_scalar_fields(label, cpp_rows)
        validate_scalar_fields(label, matlab_rows)
        comparison = compare_rows(label, cpp_rows, matlab_rows, count)
        comparison.update({"cppRows": len(cpp_rows), "matlabRows": len(matlab_rows), "expectedRows": count if count is not None else len(cpp_rows),
                           "cppSha256": cpp_sha, "matlabSha256": matlab_sha, "cppBytes": cpp_size, "matlabBytes": matlab_size})
        result["files"].append(comparison)
        total = comparison["rowMismatchCount"] + comparison["fieldMismatchCount"]
        result["allMismatchTotal"] += total
        if label in {"encoder", "syndrome", "no_error_decode", "single_error_decode"}:
            result["singleBlockMismatchTotal"] += total
        else:
            result["segmentedMismatchTotal"] += total
        write_summary_csv(out / summary_name, comparison)

    invalid_rows, invalid_sha, invalid_size = read_csv(mat / "matlab_invalid_input_audit.csv")
    invalid_failures = sum(1 for row in invalid_rows if row.get("pass") != "true")
    with (out / "invalid_input_summary.csv").open("w", newline="", encoding="ascii") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "rows", "failureCount", "sha256", "bytes"])
        writer.writerow(["matlab_invalid_input_audit", len(invalid_rows), invalid_failures, invalid_sha, invalid_size])

    matlab_metrics = load_metrics(mat / "matlab_test_summary.csv")
    summary = dict(matlab_metrics)
    by_name = {item["name"]: item for item in result["files"]}
    summary.update({
        "cppMatlabEncodedMismatch": by_name["encoder"]["fieldMismatches"].get("codewordBits", 0),
        "cppMatlabParityMismatch": by_name["encoder"]["fieldMismatches"].get("parityBits", 0),
        "cppMatlabSingleErrorSyndromeMismatch": by_name["syndrome"]["fieldMismatchCount"],
        "cppMatlabLookupPositionMismatch": by_name["syndrome"]["fieldMismatches"].get("errorPosition", 0),
        "cppMatlabNoErrorDecodeMismatch": by_name["no_error_decode"]["fieldMismatchCount"],
        "cppMatlabSingleErrorDecodeMismatch": by_name["single_error_decode"]["fieldMismatchCount"],
        "cppMatlabSegmentedNoiselessMismatch": by_name["segmented_noiseless"]["fieldMismatchCount"],
        "cppMatlabSegmentedSingleErrorMismatch": by_name["segmented_single_error"]["fieldMismatchCount"],
        "cppMatlabMultiBlockSingleErrorMismatch": by_name["multi_block_single_error"]["fieldMismatchCount"],
        "cppMatlabDoubleErrorClassificationMismatch": by_name["same_block_double_error"]["fieldMismatchCount"],
        "cppMatlabFillerBoundaryMismatch": by_name["filler_boundary"]["fieldMismatchCount"],
        "cppMatlabFailureStatusRetentionMismatch": by_name["failure_status_retention"]["fieldMismatchCount"],
        "cppMatlabFramePoolMismatch": by_name["frame_pool"]["fieldMismatchCount"],
        "cppMatlabFixedMultiErrorMismatch": by_name["fixed_multi_error"]["fieldMismatchCount"],
        "fixedMultiErrorCases": by_name["fixed_multi_error"]["cppRows"],
        "fixedMultiErrorExpectedCount": int(config["fixedMultiErrorExpectedCount"]),
        "framePoolAuditCases": by_name["frame_pool"]["cppRows"],
        "singleBlockCrossCheckMismatchTotal": result["singleBlockMismatchTotal"],
        "segmentedCrossCheckMismatchTotal": result["segmentedMismatchTotal"],
        "allCrossCheckMismatchTotal": result["allMismatchTotal"],
        "commonRegressionPassed": 0,
        "taskCommonModified": 0,
        "historicalStageModified": 0,
        "bch07Started": 0,
    })

    with (out / "test_summary.csv").open("w", newline="", encoding="ascii") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key in sorted(summary):
            writer.writerow([key, summary[key]])
    (out / "cross_check_summary.json").write_text(json.dumps(result, indent=2), encoding="ascii")
    with (out / "cross_check_summary.csv").open("w", newline="", encoding="ascii") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "cppRows", "matlabRows", "rowMismatchCount", "fieldMismatchCount",
                         "firstMismatchRow", "firstMismatchField", "cppValue", "matlabValue"])
        for item in result["files"]:
            writer.writerow([item["name"], item["cppRows"], item["matlabRows"], item["rowMismatchCount"],
                             item["fieldMismatchCount"], item["firstMismatchRow"], item["firstMismatchField"],
                             item["cppValue"], item["matlabValue"]])

    if invalid_failures or len(invalid_rows) < 20:
        print("BLOCKED_BCH06_MATLAB_INVALID_INPUT_AUDIT_FAILED")
        return 1
    if result["singleBlockMismatchTotal"] == 0:
        print("PASS_BCH06_CPP_MATLAB_SINGLE_BLOCK_CROSS_CHECK")
    if result["allMismatchTotal"] == 0:
        print("PASS_BCH06_CPP_MATLAB_SEGMENTED_CROSS_CHECK")
        return 0
    print("BLOCKED_BCH06_CPP_MATLAB_MISMATCH")
    return 1

if __name__ == "__main__":
    sys.exit(main())
