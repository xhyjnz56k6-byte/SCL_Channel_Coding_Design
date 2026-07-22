import csv,sys
with open(sys.argv[1],newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
if len(rows)!=2 or any(int(r['encoderMismatch']) or int(r['decodedPayloadMismatch']) for r in rows):raise SystemExit('BLOCKED_BCH10_TOOLBOX_CODEC_MISMATCH')
print('PASS_BCH10_TOOLBOX_CODEC_REFERENCE singleErrorCases='+str(sum(int(r['singleErrorCases']) for r in rows)))
