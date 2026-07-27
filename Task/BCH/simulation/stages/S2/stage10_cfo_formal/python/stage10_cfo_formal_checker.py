import csv, hashlib, json, math
from pathlib import Path
from PIL import Image

STAGE=Path(__file__).resolve().parents[1]; RESULTS=STAGE/"results"
with (RESULTS/"stage10_cfo_formal_result_summary.csv").open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
assert len(rows)==136
target_grid={0.5*i for i in range(17)}
assert {round(float(r["snrDb"]),12) for r in rows}==target_grid
assert len({(r["caseId"],round(float(r["snrDb"]),12)) for r in rows})==136
for r in rows:
    frames=int(r["totalFrames"]); bits=int(r["totalPayloadBits"])
    assert 1000<=frames<=50000
    assert abs(float(r["ber"])-int(r["payloadErrorBits"])/bits)<=1e-15
    assert abs(float(r["fer"])-int(r["payloadErrorFrames"])/frames)<=1e-15
    n=int(r["encodedLength"]); delta=float(r["deltaPhaseRadPerSymbol"])
    assert abs(delta-math.radians(30)/(n-1))<=1e-15
    assert abs(float(r["actualEndPhaseDeg"])-30.0)<=1e-12
    assert abs(float(r["snrDb"])-(float(r["ebn0Db"])+10*math.log10(float(r["actualRate"]))))<=1e-12
    assert r["stopReason"] in {"TARGET_FRAME_ERRORS_REACHED","MAX_FRAMES_REACHED"}
    if r["stopReason"]=="TARGET_FRAME_ERRORS_REACHED":
        assert frames>=1000 and int(r["payloadErrorFrames"])>=200
    else:
        assert frames==50000
    assert abs(float(r["snrDb"])-round(float(r["snrDb"])*2)/2)<=1e-12
assert not list(STAGE.rglob("*.pdf"))
manifests=list((STAGE/"manifests").glob("stage10_cfo_formal_plot_manifest_*.json"))
assert len(manifests)==8
for path in manifests:
    m=json.loads(path.read_text(encoding="utf-8"))
    assert m["targetSnrGridDb"]==[0.5*i for i in range(17)]
    assert m["snrStepDb"]==0.5 and m["snrMinDb"]==0.0 and m["snrMaxDb"]==8.0
    assert m["pointCountPerCase"]==17
    for key,file_key in [("sourceCsvSha256","sourceCsv"),("figureDataSha256","figureData"),("pngSha256","png")]:
        p=STAGE/m[file_key]; assert hashlib.sha256(p.read_bytes()).hexdigest()==m[key]
    Image.open(STAGE/m["png"]).verify()
print("PASS_STAGE10_CFO_FORMAL")
