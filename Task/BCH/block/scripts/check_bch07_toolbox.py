import csv, sys
if len(sys.argv)!=3: raise SystemExit('usage: check_bch07_toolbox.py cpp.csv toolbox.csv')
with open(sys.argv[1],newline='',encoding='utf-8') as f: cpp={r['caseName']:r for r in csv.DictReader(f)}
with open(sys.argv[2],newline='',encoding='utf-8') as f: tb={r['caseName']:r for r in csv.DictReader(f)}
for name,row in cpp.items():
    got=tb.get(name)
    if not got or got['generatorPolynomial']!=row['generatorPolynomial'] or int(got['toolboxT'])!=int(row['correctionCapability']):
        raise SystemExit('BLOCKED_BCH07_TOOLBOX_PARAMETER_MISMATCH '+name)
print('PASS_BCH07_TOOLBOX_PARAMETER_REFERENCE')
