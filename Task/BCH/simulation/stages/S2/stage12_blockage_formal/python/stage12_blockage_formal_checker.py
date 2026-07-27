import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from PIL import Image

STAGE = Path(__file__).resolve().parents[1]
RESULTS = STAGE / "results"
with (RESULTS / "stage12_blockage_formal_result_summary.csv").open(encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 200 and not list(STAGE.rglob("*.pdf"))
a_rows = [row for row in rows if row["experimentType"] == "RATIO"]
b_rows = [row for row in rows if row["experimentType"] == "SNR"]
assert len(a_rows) == 64 and len(b_rows) == 136

baseline = subprocess.check_output([
    "git", "show", "92d3df7ad4ecf1b9c9aac42196e740b35e88daa5:"
    "Task/BCH/simulation/stages/S2/stage12_blockage_formal/results/"
    "stage12_blockage_formal_result_summary.csv"
], text=True)
baseline_a = [row for row in csv.DictReader(baseline.splitlines()) if row["experimentType"] == "RATIO"]
assert a_rows == baseline_a

target_grid = [0.5 * i for i in range(17)]
assert {round(float(row["snrDb"]), 12) for row in b_rows} == set(target_grid)
assert len({(row["caseId"], round(float(row["snrDb"]), 12)) for row in b_rows}) == 136
with (RESULTS / "stage12_blockage_formal_points.csv").open(encoding="utf-8", newline="") as stream:
    points = list(csv.DictReader(stream))
assert len(points) == 200 and all("targetSnrDb" in row for row in points)
assert {round(float(row["targetSnrDb"]), 12) for row in points if row["experimentType"] == "SNR"} == set(target_grid)

for row in b_rows:
    n = int(row["encodedLength"])
    length = int(row["blockageLengthSymbols"])
    frames = int(row["totalFrames"])
    bits = int(row["totalPayloadBits"])
    assert length == min(n, max(1, math.floor(0.10 * n + 0.5)))
    assert 1000 <= frames <= 50000
    assert 0 <= int(row["minBlockageStart"]) <= int(row["maxBlockageStart"]) <= n - length
    assert abs(float(row["actualBlockageRatio"]) - length / n) <= 1e-12
    assert abs(float(row["ber"]) - int(row["payloadErrorBits"]) / bits) <= 1e-15
    assert abs(float(row["fer"]) - int(row["payloadErrorFrames"]) / frames) <= 1e-15
    assert abs(float(row["snrDb"]) - (float(row["ebn0Db"]) + 10 * math.log10(float(row["actualRate"])))) <= 1e-12
    assert abs(float(row["snrDb"]) - round(float(row["snrDb"]) * 2) / 2) <= 1e-12
    assert row["stopReason"] in {"TARGET_FRAME_ERRORS_REACHED", "MAX_FRAMES_REACHED"}
    if row["stopReason"] == "TARGET_FRAME_ERRORS_REACHED":
        assert frames >= 1000 and int(row["payloadErrorFrames"]) >= 200
    else:
        assert frames == 50000

manifests = list((STAGE / "manifests").glob("stage12_blockage_formal_plot_manifest_*.json"))
assert len(manifests) == 10
for path in manifests:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if "vs_snr" in path.name:
        assert manifest["targetSnrGridDb"] == target_grid
        assert manifest["snrStepDb"] == 0.5
        assert manifest["pointCountPerCase"] == 17
    for hash_key, file_key in [("sourceCsvSha256", "sourceCsv"), ("figureDataSha256", "figureData"), ("pngSha256", "png")]:
        artifact = STAGE / manifest[file_key]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == manifest[hash_key]
    Image.open(STAGE / manifest["png"]).verify()
print("PASS_STAGE12_BLOCKAGE_FORMAL_DENSE_SNR")
