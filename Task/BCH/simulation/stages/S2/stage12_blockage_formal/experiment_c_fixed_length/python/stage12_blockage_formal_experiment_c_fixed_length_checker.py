import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

EXPERIMENT = Path(__file__).resolve().parents[1]
RESULTS = EXPERIMENT / "results"
SUMMARY = RESULTS / "stage12_blockage_formal_experiment_c_fixed_length_result_summary.csv"

with SUMMARY.open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

assert len(rows) == 32
assert not list(EXPERIMENT.rglob("*.pdf"))
assert {int(r["requestedBlockageLengthSymbols"]) for r in rows} == {5, 10, 20, 30}
assert len({(r["caseId"], r["requestedBlockageLengthSymbols"]) for r in rows}) == 32

for row in rows:
    encoded_length = int(row["encodedLength"])
    requested_length = int(row["requestedBlockageLengthSymbols"])
    actual_length = int(row["blockageLengthSymbols"])
    frames = int(row["totalFrames"])
    payload_bits = int(row["totalPayloadBits"])
    assert row["experimentType"] == "FIXED_LENGTH"
    assert actual_length == requested_length <= encoded_length
    assert 5000 <= frames <= 50000
    assert 0 <= int(row["minBlockageStart"]) <= int(row["maxBlockageStart"]) <= encoded_length - actual_length
    assert int(row["totalBlockedSymbols"]) == frames * actual_length
    assert abs(float(row["actualBlockageRatio"]) - actual_length / encoded_length) <= 1e-12
    assert abs(float(row["ber"]) - int(row["payloadErrorBits"]) / payload_bits) <= 1e-15
    assert abs(float(row["fer"]) - int(row["payloadErrorFrames"]) / frames) <= 1e-15
    assert abs(
        float(row["miscorrectionRate"]) - int(row["miscorrectionFrames"]) / frames
    ) <= 1e-15
    assert int(row["trueSuccessFrames"]) + int(row["payloadErrorFrames"]) == frames
    assert abs(
        float(row["snrDb"])
        - (float(row["ebn0Db"]) + 10 * math.log10(float(row["actualRate"])))
    ) <= 1e-12

manifests = list(
    (EXPERIMENT / "manifests").glob(
        "stage12_blockage_formal_experiment_c_fixed_length_*_plot_manifest.json"
    )
)
assert len(manifests) == 6
for path in manifests:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["xAxis"] == "遮挡长度"
    for hash_key, file_key in [
        ("sourceCsvSha256", "sourceCsv"),
        ("figureDataSha256", "figureData"),
        ("pngSha256", "png"),
    ]:
        artifact = EXPERIMENT / manifest[file_key]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == manifest[hash_key]
    Image.open(EXPERIMENT / manifest["png"]).verify()

print("PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_C_FIXED_LENGTH")
