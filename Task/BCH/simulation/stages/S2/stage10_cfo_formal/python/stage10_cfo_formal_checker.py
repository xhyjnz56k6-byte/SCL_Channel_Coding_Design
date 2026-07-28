import csv, hashlib, json, math
from pathlib import Path
from PIL import Image

STAGE=Path(__file__).resolve().parents[1]; RESULTS=STAGE/"results"
with (RESULTS/"stage10_cfo_formal_result_summary.csv").open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
assert len(rows)==40
for r in rows:
    frames=int(r["totalFrames"]); bits=int(r["totalPayloadBits"])
    assert 5000<=frames<=50000
    assert abs(float(r["ber"])-int(r["payloadErrorBits"])/bits)<=1e-15
    assert abs(float(r["fer"])-int(r["payloadErrorFrames"])/frames)<=1e-15
    n=int(r["encodedLength"]); delta=float(r["deltaPhaseRadPerSymbol"])
    assert abs(delta-math.radians(30)/(n-1))<=1e-15
    assert abs(float(r["actualEndPhaseDeg"])-30.0)<=1e-12
    assert abs(float(r["snrDb"])-(float(r["ebn0Db"])+10*math.log10(float(r["actualRate"]))))<=1e-12
assert not list(STAGE.rglob("*.pdf"))
manifests=list((STAGE/"manifests").glob("stage10_cfo_formal_plot_manifest_*.json"))
assert len(manifests)==8
for path in manifests:
    m=json.loads(path.read_text(encoding="utf-8"))
    for key,file_key in [("sourceCsvSha256","sourceCsv"),("figureDataSha256","figureData"),("pngSha256","png")]:
        p=STAGE/m[file_key]; assert hashlib.sha256(p.read_bytes()).hexdigest()==m[key]
    Image.open(STAGE/m["png"]).verify()
print("PASS_STAGE10_CFO_FORMAL")
