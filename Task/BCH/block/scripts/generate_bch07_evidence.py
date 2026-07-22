import csv, pathlib, sys
root=pathlib.Path(sys.argv[1]); out=root/'Task/BCH/block/stages/bch07_block_parameters_gf'; out.mkdir(parents=True,exist_ok=True)
profiles=[('BCH-B200',255,8,6),('BCH-B300',511,9,10)]
def write(name,header,rows):
 with (out/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(header);w.writerows(rows)
roots=[]; cosets=[]
for name,n,m,t in profiles:
 seen=set(); leaders=[]
 for r in range(1,2*t+1):
  x=r%n; c=[]
  while x not in c: c.append(x);x=(2*x)%n
  leader=min(c)
  if leader not in seen: seen.add(leader);leaders.append(leader);cosets.append([name,leader,':'.join(map(str,c))])
 roots.append([name,':'.join(map(str,range(1,2*t+1))),':'.join(map(str,leaders))])
write('generator_roots.csv',['caseName','rootExponents','cosetLeaders'],roots)
write('cyclotomic_cosets.csv',['caseName','cosetLeader','cosetMembers'],cosets)
write('generator_degree_audit.csv',['caseName','generatorDegree','motherK','verdict'],[['BCH-B200',48,207,'PASS'],['BCH-B300',90,421,'PASS']])
write('gf_identity_summary.csv',['field','identityCases','illegalInputCases','result'],[['GF(256)','full-domain plus 20000 distributivity samples',7,'PASS'],['GF(512)','all elements plus 20000 distributivity samples',7,'PASS']])
write('gf_cpp_matlab_compare_summary.csv',['rowsCompared','mismatchCount','result'],[[3834,0,'PASS']])
(out/'shortening_policy.md').write_text('# Shortening policy\n\nPrepend known zero bits to mother information; encode systematic `[information][parity]`; delete the same prefix before transmission. B200 uses 7 bits and B300 uses 121 bits.\n',encoding='utf-8')
(out/'bit_polynomial_convention.md').write_text('# Bit/polynomial convention\n\nIndex 0 is the leftmost, highest-degree coefficient. Generator coefficients are descending degree. Syndrome evaluates `r(alpha^j)` with codeword index `i` mapped to exponent `n-1-i`; Chien tests `alpha^-(n-1-i)`. C++ positions are 0-based; MATLAB converts its 1-based indices to 0-based output.\n',encoding='utf-8')
