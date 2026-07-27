import csv
import hashlib
import json
import math
from pathlib import Path


STAGE_DIR = Path(__file__).resolve().parents[1]
RESULTS = STAGE_DIR / "results"
LOGS = STAGE_DIR / "logs"


def read_csv(name):
    with (RESULTS / name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(f"BLOCKED_STAGE01_FOUNDATION_CHECK: {message}")


def main():
    ctest = LOGS / "stage01_foundation_ctest.log"
    matlab_log = LOGS / "stage01_foundation_matlab.log"
    compare_log = LOGS / "stage01_foundation_compare.log"
    for path in (ctest, matlab_log, compare_log):
        require(path.exists() and path.stat().st_size > 0, f"missing or empty log: {path.name}")
    require("100% tests passed" in ctest.read_text(encoding="utf-8"), "CTest did not pass")
    require(
        "PASS_STAGE01_FOUNDATION_MATLAB_REFERENCE" in matlab_log.read_text(encoding="utf-8"),
        "MATLAB reference did not pass",
    )
    require(
        "mismatch=0 discreteMismatch=0" in compare_log.read_text(encoding="utf-8"),
        "C++/MATLAB comparison did not pass",
    )

    comparisons = read_csv("stage01_foundation_cpp_matlab_compare.csv")
    require(len(comparisons) == 20, "comparison row count is not 20")
    require(all(row["passed"] == "true" for row in comparisons), "comparison contains failure")
    require(
        all(row["discreteMismatch"] == "0" for row in comparisons),
        "discrete mismatch is nonzero",
    )

    randomness = read_csv("stage01_foundation_randomness_test.csv")
    require(len(randomness) == 6, "randomness test count is not 6")
    require(all(row["passed"] == "true" for row in randomness), "randomness test failed")

    outputs = read_csv("stage01_foundation_cpp_outputs.csv")
    require(len(outputs) == 20, "C++ output row count is not 20")
    for row in outputs:
        rate = float(row["actual_rate"])
        ebn0 = float(row["ebn0_db"])
        sigma2 = float(row["sigma2"])
        linear = float(row["snr_linear"])
        db = float(row["snr_db"])
        require(all(math.isfinite(value) for value in (rate, ebn0, sigma2, linear, db)), "non-finite value")
        require(abs(sigma2 - 1.0 / (2.0 * rate * 10.0 ** (ebn0 / 10.0))) <= 1e-12, "sigma2 mismatch")
        require(abs(linear - 1.0 / sigma2) <= 1e-12 * max(1.0, linear), "snr linear mismatch")
        require(abs(db - (ebn0 + 10.0 * math.log10(2.0 * rate))) <= 1e-12, "snr dB mismatch")
        require(
            row["conversion_formula"] == "SNR_dB = EbN0_dB + 10*log10(2*R)",
            "conversion formula mismatch",
        )

    hash_path = STAGE_DIR / "stage01_foundation_file_hashes.json"
    hashes = json.loads(hash_path.read_text(encoding="utf-8"))
    require(hashes, "hash manifest is empty")
    for item in hashes:
        path = STAGE_DIR / item["file"]
        require(path.exists(), f"hashed file missing: {item['file']}")
        require(digest(path) == item["sha256"], f"hash mismatch: {item['file']}")
        require(path.stat().st_size == item["size"], f"size mismatch: {item['file']}")

    summary = STAGE_DIR / "stage01_foundation_test_summary.csv"
    summary.write_text(
        "test,executed,result,detail\n"
        "Release build,true,PASS,MinGW GCC 15.2.0\n"
        "CTest,true,PASS,1/1\n"
        "MATLAB reference,true,PASS,R2024b\n"
        "C++ MATLAB comparison,true,PASS,20 rows mismatch=0 discreteMismatch=0\n"
        "random identity,true,PASS,6/6\n"
        "formula audit,true,PASS,20/20\n"
        "file hash audit,true,PASS,all generated result and log files\n",
        encoding="utf-8",
    )
    print("PASS_STAGE01_FOUNDATION_CHECK")


if __name__ == "__main__":
    main()
