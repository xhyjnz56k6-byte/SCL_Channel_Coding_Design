import csv,sys
def read(p):
 with open(p,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
a,b=read(sys.argv[1]),read(sys.argv[2])
if a!=b:raise SystemExit('BLOCKED_BCH07_GF_CPP_MATLAB_MISMATCH')
print('PASS_BCH07_GF_CPP_MATLAB_DETAIL rows='+str(len(a)))
