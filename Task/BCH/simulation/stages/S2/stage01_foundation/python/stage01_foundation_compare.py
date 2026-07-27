import argparse
import csv
import math
from pathlib import Path


FLOAT_COLUMNS = (
    "actual_rate",
    "ebn0_db",
    "z",
    "sigma2",
    "sigma",
    "noise",
    "transmitted",
    "received",
    "snr_linear",
    "snr_db",
)
EXACT_COLUMNS = (
    "rowId",
    "payloadLength",
    "encodedLength",
    "bit",
    "hard_decision",
    "conversion_formula",
)


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", type=Path, required=True)
    parser.add_argument("--matlab", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cpp_rows = read_rows(args.cpp)
    matlab_rows = read_rows(args.matlab)
    if len(cpp_rows) != len(matlab_rows) or not cpp_rows:
        raise SystemExit("BLOCKED_STAGE01_FOUNDATION_COMPARE: row count mismatch")

    output_rows = []
    mismatch_count = 0
    discrete_mismatch = 0
    tolerance = 1e-12
    for cpp, matlab in zip(cpp_rows, matlab_rows):
        max_abs_error = 0.0
        row_mismatch = False
        for column in FLOAT_COLUMNS:
            left = float(cpp[column])
            right = float(matlab[column])
            if not math.isfinite(left) or not math.isfinite(right):
                row_mismatch = True
                max_abs_error = math.inf
                continue
            error = abs(left - right)
            max_abs_error = max(max_abs_error, error)
            if error > tolerance * max(1.0, abs(left), abs(right)):
                row_mismatch = True
        for column in EXACT_COLUMNS:
            if cpp[column] != matlab[column]:
                row_mismatch = True
                if column == "hard_decision":
                    discrete_mismatch += 1
        mismatch_count += int(row_mismatch)
        output_rows.append(
            {
                "rowId": cpp["rowId"],
                "maxAbsError": f"{max_abs_error:.17g}",
                "continuousTolerance": f"{tolerance:.1e}",
                "discreteMismatch": int(cpp["hard_decision"] != matlab["hard_decision"]),
                "passed": str(not row_mismatch).lower(),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)
    if mismatch_count or discrete_mismatch:
        raise SystemExit(
            f"BLOCKED_STAGE01_FOUNDATION_COMPARE: mismatch={mismatch_count}, "
            f"discreteMismatch={discrete_mismatch}"
        )
    print(
        f"PASS_STAGE01_FOUNDATION_CPP_MATLAB_COMPARE rows={len(output_rows)} "
        f"mismatch=0 discreteMismatch=0"
    )


if __name__ == "__main__":
    main()
