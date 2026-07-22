import csv,sys
def read(p):
 with open(p,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
a,b=read(sys.argv[1]),read(sys.argv[2])
if a!=b:raise SystemExit('BLOCKED_BCH10_ILLEGAL_INPUT_MISMATCH')
print('PASS_BCH10_ILLEGAL_INPUT_REFERENCE rows='+str(len(a)))
