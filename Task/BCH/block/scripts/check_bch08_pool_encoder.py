import csv,sys
def read(p):
 with open(p,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
a,b=read(sys.argv[1]),read(sys.argv[2])
if len(a)!=200 or a!=b:raise SystemExit('BLOCKED_BCH08_POOL_ENCODER_MISMATCH')
if any(r['divisible'] not in {'1','true'} for r in a):raise SystemExit('BLOCKED_BCH08_MOTHER_CODEWORD_NOT_DIVISIBLE')
print('PASS_BCH08_POOL_ENCODER_REFERENCE')
