#!/usr/bin/env python3
"""Validate the committed BCH-04 decoder audit CSV summaries."""

import csv
import pathlib
import sys


def read_metric_csv(path: pathlib.Path) -> dict[str, int]:
    text = path.read_text(encoding="ascii")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise ValueError(f"control character in {path.name}")
    rows = list(csv.reader(text.splitlines()))
    if not rows or rows[0] != ["metric", "value"]:
        raise ValueError(f"metric header mismatch: {path.name}")
    return {row[0]: int(row[1]) for row in rows[1:]}


def expect(metrics: dict[str, int], key: str, value: int) -> None:
    if metrics.get(key) != value:
        raise ValueError(f"{key} expected {value}, got {metrics.get(key)}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_bch04_lookup_decoder.py <stage-directory>", file=sys.stderr)
        return 2
    stage = pathlib.Path(sys.argv[1])
    no_error = read_metric_csv(stage / "no_error_summary.csv")
    single = read_metric_csv(stage / "single_error_summary.csv")
    double = read_metric_csv(stage / "double_error_audit.csv")
    summary = read_metric_csv(stage / "test_summary.csv")
    expect(no_error, "noErrorCaseCount", 2048)
    for key in ("noErrorPayloadMismatch", "noErrorCodewordMismatch", "noErrorStatusMismatch", "noErrorLookupHitMismatch", "noErrorSyndromeMismatch"):
        expect(no_error, key, 0)
    expect(single, "singleErrorCaseCount", 30720)
    for key in ("singleErrorPayloadMismatch", "singleErrorCodewordMismatch", "correctedPositionMismatch", "postSyndromeMismatch", "lookupMissForSingleError", "singleErrorStatusMismatch", "singleErrorSyndromeBeforeMismatch"):
        expect(single, key, 0)
    expected_double = {
        "doubleErrorCaseCount": 215040,
        "doubleErrorCorrectedStatusCount": 215040,
        "doubleErrorNoErrorStatusCount": 0,
        "doubleErrorPostCheckFailedCount": 0,
        "doubleErrorUnrecognizedCount": 0,
        "doubleErrorLookupHitCount": 215040,
        "doubleErrorPostSyndromeZeroCount": 215040,
        "decodedToOriginalCodeword": 0,
        "decodedToOriginalPayload": 0,
        "miscorrectedToAnotherValidCodeword": 215040,
        "reportedCorrectedButPayloadWrong": 215040,
    }
    for key, value in expected_double.items():
        expect(double, key, value)
    expect(summary, "fixedSeedCaseCount", 48)
    for key in ("unrecognizedSyndromeStatusMismatch", "postCheckFailedStatusMismatch", "invalidTablePositionMismatch", "invalidInputMismatch"):
        expect(summary, key, 0)
    multi = list(csv.DictReader((stage / "multi_error_seed_audit.csv").open(encoding="ascii", newline="")))
    if len(multi) != 48:
        raise ValueError(f"multi-error row count expected 48, got {len(multi)}")
    if {row["seedId"] for row in multi} != {f"T3_{i:02d}" for i in range(1, 7)} | {f"T4_{i:02d}" for i in range(1, 7)}:
        raise ValueError("multi-error seed IDs mismatch")
    print("PASS_BCH04_LOOKUP_DECODER_AUDIT_CSV")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, csv.Error) as error:
        print(f"FAIL_BCH04_LOOKUP_DECODER_AUDIT_CSV: {error}", file=sys.stderr)
        raise SystemExit(1)
