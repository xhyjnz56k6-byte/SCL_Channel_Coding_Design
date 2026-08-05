import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def round_half_up(value):
    return math.floor(value + 0.5)


def check_scheme(root: Path, scheme: str, workpoints: dict) -> dict:
    path = root / "results" / scheme.lower() / "all_start_results.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    encoded = 285 if scheme == "BCH" else 612
    payload = 200 if scheme == "BCH" else 300
    expected_groups = 3 * sum(encoded - round_half_up(ratio * encoded) + 1 for ratio in (0.05, 0.10))
    require(len(rows) == expected_groups * 4, f"{scheme}: row count mismatch")
    groups = defaultdict(list)
    for row in rows:
        require(row["scheme"] == scheme, f"{scheme}: scheme mismatch")
        require(row["pureMethodDifferenceAllowed"] == "false", f"{scheme}: pure method claim forbidden")
        require(int(row["framesProcessed"]) == 200, f"{scheme}: frames mismatch")
        require(int(row["totalBits"]) == 200 * payload, f"{scheme}: total bits mismatch")
        require(int(row["bitErrors"]) / int(row["totalBits"]) == float(row["BER"]), f"{scheme}: BER mismatch")
        require(int(row["frameErrors"]) / 200 == float(row["FER"]), f"{scheme}: FER mismatch")
        require(math.isfinite(float(row["BER"])) and math.isfinite(float(row["FER"])), f"{scheme}: NaN/Inf")
        key = (row["workpointRole"], row["EsN0Db"], row["burstRatioRequested"], row["burstStart"])
        groups[key].append(row)
    require(len(groups) == expected_groups, f"{scheme}: group count mismatch")
    expected_snrs = {
        "LOW": float(workpoints["lowEsN0Db"]),
        "WATERFALL": float(workpoints["waterfallEsN0Db"]),
        "HIGH": float(workpoints["highEsN0Db"]),
    }
    for key, group in groups.items():
        require(len(group) == 4, f"{scheme}: incomplete comparison group")
        role, snr_text, ratio_text, start_text = key
        require(float(snr_text) == expected_snrs[role], f"{scheme}: workpoint mismatch")
        ratio, start = float(ratio_text), int(start_text)
        length = round_half_up(ratio * encoded)
        require(0 <= start <= encoded - length, f"{scheme}: invalid start")
        for field in ("framesProcessed", "payloadChecksum", "noiseChecksum", "frameSequenceHash"):
            require(len({row[field] for row in group}) == 1, f"{scheme}: shared {field} mismatch")
    for role in expected_snrs:
        for ratio in (0.05, 0.10):
            length = round_half_up(ratio * encoded)
            starts = {int(row["burstStart"]) for row in rows if row["workpointRole"] == role and float(row["burstRatioRequested"]) == ratio}
            require(starts == set(range(encoded - length + 1)), f"{scheme}: missing/extra exhaustive starts")
    checkpoint = json.loads((root / "results" / scheme.lower() / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    require(checkpoint["status"] == "COMPLETE" and checkpoint["completedGroups"] == expected_groups, f"{scheme}: checkpoint incomplete")
    return {"rows": len(rows), "groups": len(groups), "expectedGroups": expected_groups}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "stage12_all_start_scan"
    workpoints = json.loads((root / "selected_workpoints.json").read_text(encoding="utf-8"))["schemes"]
    report = {scheme: check_scheme(root, scheme, workpoints[scheme]) for scheme in ("BCH", "CC")}
    report.update({"status": "PASS", "mergeStatus": "NOT_MERGED"})
    (root / "results" / "stage12_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS_S7_STAGE12 BCH={report['BCH']['rows']} CC={report['CC']['rows']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FAIL_S7_STAGE12: {error}", file=sys.stderr)
        raise
