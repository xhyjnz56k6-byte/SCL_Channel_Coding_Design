import csv,hashlib,json,math
from pathlib import Path
from PIL import Image
STAGE=Path(__file__).resolve().parents[1];R=STAGE/"results"
with (R/"stage12_blockage_formal_result_summary.csv").open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f))
assert len(rows)==104 and not list(STAGE.rglob("*.pdf"))
for r in rows:
 n=int(r["encodedLength"]);l=int(r["blockageLengthSymbols"]);frames=int(r["totalFrames"]);bits=int(r["totalPayloadBits"])
 assert 5000<=frames<=50000 and 0<=int(r["minBlockageStart"])<=int(r["maxBlockageStart"])<=n-l
 expected=0 if float(r["requestedBlockageRatio"])==0 else min(n,max(1,math.floor(float(r["requestedBlockageRatio"])*n+.5)))
 assert l==expected and abs(float(r["actualBlockageRatio"])-l/n)<=1e-12
 assert abs(float(r["ber"])-int(r["payloadErrorBits"])/bits)<=1e-15
 assert abs(float(r["fer"])-int(r["payloadErrorFrames"])/frames)<=1e-15
 assert abs(float(r["snrDb"])-(float(r["ebn0Db"])+10*math.log10(float(r["actualRate"]))))<=1e-12
manifests=list((STAGE/"manifests").glob("stage12_blockage_formal_plot_manifest_*.json"));assert len(manifests)==10
for p in manifests:
 m=json.loads(p.read_text(encoding="utf-8"))
 for hk,fk in [("sourceCsvSha256","sourceCsv"),("figureDataSha256","figureData"),("pngSha256","png")]:
  q=STAGE/m[fk];assert hashlib.sha256(q.read_bytes()).hexdigest()==m[hk]
 Image.open(STAGE/m["png"]).verify()
print("PASS_STAGE12_BLOCKAGE_FORMAL")
