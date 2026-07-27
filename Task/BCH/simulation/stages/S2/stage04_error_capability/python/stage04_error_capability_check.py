import csv
from collections import Counter
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"
ALLOWED = {
    "TRUE_SUCCESS", "DETECTED_FAILURE", "MISCORRECTION",
    "UNDETECTED_ERROR", "INVALID_CONFIGURATION",
}


def rows(name):
    with (RESULTS / name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise SystemExit(f"BLOCKED_STAGE04_ERROR_CAPABILITY_CHECK: {message}")


def main():
    results = rows("stage04_error_capability_results.csv")
    require(results, "results are empty")
    require(all(row["status"] in ALLOWED for row in results), "unknown status")
    guaranteed = [row for row in results if row["withinCapability"] in ("1", "true")]
    require(guaranteed, "guaranteed set is empty")
    require(all(row["guaranteePass"] in ("1", "true") and row["status"] == "TRUE_SUCCESS"
                for row in guaranteed), "0..t guarantee failed")
    beyond = [row for row in results if int(row["errorWeight"]) > 0 and
              row["withinCapability"] in ("0", "false")]
    require(beyond, "over-capability set is empty")
    require(all(row["status"] != "INVALID_CONFIGURATION" for row in results),
            "invalid configuration occurred")

    cases = rows("stage04_error_capability_cases.csv")
    require(len(cases) == len(results), "case/result row count mismatch")
    for case_id in ("K200_S15", "K300_S15"):
        single = [row for row in cases if row["caseId"] == case_id and
                  row["patternName"] == "BCH15_SINGLE_ALL_POSITIONS"]
        require(len(single) == 15, f"{case_id} does not cover all 15 single-error positions")
        require(any(row["patternName"] == "BCH15_DOUBLE_SAME_BLOCK" for row in cases
                    if row["caseId"] == case_id), f"{case_id} same-block double missing")
        require(any(row["patternName"] == "BCH15_DOUBLE_CROSS_BLOCK" for row in cases
                    if row["caseId"] == case_id), f"{case_id} cross-block double missing")
        require(any(row["patternName"] == "BCH15_ONE_ERROR_EACH_BLOCK" for row in cases
                    if row["caseId"] == case_id), f"{case_id} one-error-each-block missing")
    require(any(row["caseId"] == "K300_M255K207" and
                row["patternName"] == "MULTIBLOCK_ONE_ERROR_EACH_BLOCK" for row in cases),
            "K300 M255 multi-block boundary case missing")

    summary = rows("stage04_error_capability_status_summary.csv")
    require(len(summary) == 8, "summary case count is not 8")
    for row in summary:
        total = sum(int(row[name]) for name in ALLOWED)
        require(total == int(row["totalPatterns"]), f"{row['caseId']} status accounting mismatch")
        require(int(row["withinCapabilityFailures"]) == 0, "within capability failure recorded")
        require(row["stopReason"] == "ERROR_CAPABILITY_FIXED_CASES", "stop reason mismatch")

    matlab = rows("stage04_error_capability_cpp_matlab_compare.csv")
    require(len(matlab) == 16, "MATLAB key sample count is not 16")
    require(all(row["passed"] in ("1", "true") and row["recoveredMismatchBits"] == "0"
                for row in matlab), "MATLAB key sample mismatch")
    ctest = (LOGS / "stage04_error_capability_ctest.log").read_text(encoding="utf-8")
    require("100% tests passed" in ctest and "PASS_STAGE04_ERROR_CAPABILITY" in ctest,
            "CTest Gate failed")
    matlab_log = (LOGS / "stage04_error_capability_matlab.log").read_text(encoding="utf-8")
    require("PASS_STAGE04_ERROR_CAPABILITY_MATLAB_REFERENCE" in matlab_log, "MATLAB Gate failed")
    status_counts = Counter(row["status"] for row in beyond)
    detail = "|".join(f"{key}:{status_counts.get(key,0)}" for key in sorted(ALLOWED))
    (STAGE / "stage04_error_capability_test_summary.csv").write_text(
        "test,executed,result,detail\n"
        f"0..t guaranteed recovery,true,PASS,{len(guaranteed)} patterns\n"
        f"t+1 and t+2 classification,true,PASS,{len(beyond)} patterns;{detail}\n"
        "BCH15 all single positions,true,PASS,30 patterns\n"
        "BCH15 same/cross/multi-block,true,PASS,6 patterns\n"
        "K300 M255 cross-block,true,PASS,1 pattern\n"
        "C++ MATLAB key samples,true,PASS,16/16\n",
        encoding="utf-8",
    )
    print("PASS_STAGE04_ERROR_CAPABILITY_CHECK")


if __name__ == "__main__":
    main()
