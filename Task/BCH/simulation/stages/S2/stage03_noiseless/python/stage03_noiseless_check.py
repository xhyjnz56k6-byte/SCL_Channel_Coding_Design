import csv
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
LOGS = STAGE / "logs"


def rows(name):
    with (RESULTS / name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise SystemExit(f"BLOCKED_STAGE03_NOISELESS_CHECK: {message}")


def main():
    summary = rows("stage03_noiseless_case_summary.csv")
    require(len(summary) == 8, "case summary count is not 8")
    for row in summary:
        require(int(row["totalFrames"]) == 1007, f"{row['caseId']} frame count mismatch")
        require(int(row["totalPayloadBits"]) == 1007 * int(row["caseId"][1:4]),
                f"{row['caseId']} payload bit denominator mismatch")
        for field in (
            "payloadErrorBits", "payloadErrorFrames", "decoderFailureFrames",
            "miscorrectionFrames", "undetectedErrorFrames",
        ):
            require(int(row[field]) == 0, f"{row['caseId']} {field} is nonzero")
        require(int(row["trueSuccessFrames"]) == int(row["totalFrames"]),
                f"{row['caseId']} true success mismatch")
        require(float(row["ber"]) == 0.0 and float(row["fer"]) == 0.0,
                f"{row['caseId']} BER/FER is nonzero")
        require(row["stopReason"] == "NOISELESS_FIXED_FRAMES", "stop reason mismatch")

    detail = rows("stage03_noiseless_results.csv")
    require(len(detail) == 8056, "detail row count is not 8056")
    require(all(row["payloadErrorBits"] == "0" and row["trueSuccess"] == "1" for row in detail),
            "detail contains mismatch")
    matlab = rows("stage03_noiseless_cpp_matlab_compare.csv")
    require(len(matlab) == 8, "MATLAB sample count is not 8")
    require(all(row["passed"] in ("1", "true") and row["encodedMismatchBits"] == "0"
                and row["recoveredMismatchBits"] == "0" for row in matlab),
            "MATLAB sample comparison failed")
    ctest = (LOGS / "stage03_noiseless_ctest.log").read_text(encoding="utf-8")
    require("100% tests passed" in ctest and "PASS_STAGE03_NOISELESS" in ctest, "CTest Gate failed")
    matlab_log = (LOGS / "stage03_noiseless_matlab.log").read_text(encoding="utf-8")
    require("PASS_STAGE03_NOISELESS_MATLAB_REFERENCE" in matlab_log, "MATLAB Gate failed")
    (STAGE / "stage03_noiseless_test_summary.csv").write_text(
        "test,executed,result,detail\n"
        "Release build,true,PASS,MinGW GCC 15.2.0\n"
        "CTest,true,PASS,1/1\n"
        "fixed and boundary payloads,true,PASS,7 per case\n"
        "random noiseless frames,true,PASS,1000 per case\n"
        "all noiseless frames,true,PASS,8056 total\n"
        "C++ MATLAB samples,true,PASS,8/8 encoded and recovered mismatch=0\n"
        "negative/error counters,true,PASS,all zero\n",
        encoding="utf-8",
    )
    print("PASS_STAGE03_NOISELESS_CHECK")


if __name__ == "__main__":
    main()
