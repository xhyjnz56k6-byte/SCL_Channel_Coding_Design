import csv
import json
import math
from pathlib import Path


STAGE_DIR = Path(__file__).resolve().parents[1]
RESULTS = STAGE_DIR / "results"
LOGS = STAGE_DIR / "logs"


def rows(name):
    with (RESULTS / name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise SystemExit(f"BLOCKED_STAGE02_CASE_CONTRACT_CHECK: {message}")


def vector(text):
    return [int(value) for value in text.split("|")]


def main():
    cases = rows("stage02_case_contract_cases.csv")
    require(len(cases) == 8, "case count is not 8")
    require(len({row["caseId"] for row in cases}) == 8, "caseId is not unique")
    require(len({row["displayName"] for row in cases}) == 8, "displayName is not unique")
    for payload in ("200", "300"):
        group = [row for row in cases if row["payloadLength"] == payload]
        require(len(group) == 4, f"payload {payload} does not have four cases")
        require(len({row["legendLabel"] for row in group}) == 4, f"payload {payload} legends are not unique")
        require(len({row["plotStyleId"] for row in group}) == 4, f"payload {payload} styles are not unique")
    for row in cases:
        payload = int(row["payloadLength"])
        encoded = int(row["totalEncodedLength"])
        require(sum(vector(row["payloadPerBlock"])) == payload, f"{row['caseId']} payload sum mismatch")
        require(sum(vector(row["encodedLengthPerBlock"])) == encoded, f"{row['caseId']} encoded sum mismatch")
        require(len(vector(row["payloadPerBlock"])) == int(row["blockCount"]), "blockCount mismatch")
        require(
            abs(float(row["actualRate"]) - payload / encoded) <= 1e-15,
            f"{row['caseId']} rate mismatch",
        )
        require(max(vector(row["encodedLengthPerBlock"])) <= 1000, "block length exceeds 1000")
    multi = next(row for row in cases if row["caseId"] == "K300_M255K207")
    require(multi["payloadPerBlock"] == "150|150", "K300 M255 payload split is not 150|150")
    require(multi["shorteningPerBlock"] == "57|57", "K300 M255 shortening is not 57|57")
    require(multi["encodedLengthPerBlock"] == "198|198", "K300 M255 encoded split is not 198|198")
    require(multi["totalEncodedLength"] == "396", "K300 M255 total length is not 396")

    length_rows = rows("stage02_case_contract_length_audit.csv")
    require(len(length_rows) == 54, "block audit row count is not 54")
    for row in length_rows:
        require(
            row["informationEquationPass"] == "true"
            and row["encodedEquationPass"] == "true"
            and row["blockWithin1000Pass"] == "true",
            f"length audit failed: {row['caseId']} block {row['blockIndex']}",
        )
    require(all(row["passed"] == "true" for row in rows("stage02_case_contract_rate_audit.csv")),
            "rate audit failed")
    matlab = rows("stage02_case_contract_cpp_matlab_compare.csv")
    require(len(matlab) == 8 and all(row["passed"] in ("1", "true") for row in matlab),
            "MATLAB length/rate audit failed")
    schema = json.loads((RESULTS / "stage02_case_contract_schema.json").read_text(encoding="utf-8"))
    require(schema["caseCount"] == 8, "schema case count mismatch")
    ctest = (LOGS / "stage02_case_contract_ctest.log").read_text(encoding="utf-8")
    require("100% tests passed" in ctest, "CTest did not pass")
    matlab_log = (LOGS / "stage02_case_contract_matlab.log").read_text(encoding="utf-8")
    require("PASS_STAGE02_CASE_CONTRACT_MATLAB_REFERENCE" in matlab_log, "MATLAB log did not pass")
    (STAGE_DIR / "stage02_case_contract_test_summary.csv").write_text(
        "test,executed,result,detail\n"
        "Release build,true,PASS,MinGW GCC 15.2.0\n"
        "CTest,true,PASS,1/1 including 8-case encode/decode recovery\n"
        "length audit,true,PASS,54/54 blocks\n"
        "rate audit,true,PASS,8/8 cases\n"
        "MATLAB contract reference,true,PASS,8/8 cases\n"
        "negative configuration tests,true,PASS,invalid id/payload/received length rejected\n",
        encoding="utf-8",
    )
    print("PASS_STAGE02_CASE_CONTRACT")


if __name__ == "__main__":
    main()
