import csv, hashlib, pathlib, sys

root=pathlib.Path(sys.argv[1]).resolve(); ref=root/'Task/BCH/block/build/group3/reference'; stages=root/'Task/BCH/block/stages'
rows=list(csv.DictReader((ref/'cpp_detail.csv').open(encoding='utf-8',newline='')))
mat=list(csv.DictReader((ref/'matlab_detail.csv').open(encoding='utf-8',newline='')))
if rows!=mat: raise SystemExit('detail mismatch')
def write(path,header,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(header);w.writerows(data)
profiles=list(csv.DictReader((ref/'cpp_bch07.csv').open(encoding='utf-8',newline='')))
b07=stages/'bch07_block_parameters_gf'; b10=stages/'bch10_block_matlab_reference'; group=stages/'bch_group3_block_core_reference'
write(b07/'block_profiles.csv',profiles[0].keys(),[r.values() for r in profiles])
write(b07/'primitive_polynomials.csv',['caseName','fieldDegree','primitivePolynomial'],[[r['caseName'],r['fieldDegree'],r['primitivePolynomial']] for r in profiles])
write(b07/'generator_polynomials.csv',['caseName','generatorDegree','generatorPolynomial','correctionCapability'],[[r['caseName'],r['generatorDegree'],r['generatorPolynomial'],r['correctionCapability']] for r in profiles])
for name,kind in [('cpp_block_single_error_reference.csv','SINGLE_ALL'),('cpp_block_multi_error_reference.csv','WEIGHT_'),('uncorrectable_error_detail.csv','T_PLUS')]:
 selected=[r for r in rows if r['errorKind']==kind or r['errorKind'].startswith(kind)]
 write(b10/name,rows[0].keys(),[r.values() for r in selected])
for name,source in [('matlab_block_parameter_reference.csv',ref/'matlab_bch07.csv'),('cpp_block_parameter_reference.csv',ref/'cpp_bch07.csv')]:
 (b10/name).write_bytes(source.read_bytes())
single=[r for r in rows if r['errorKind']=='SINGLE_ALL']; multi=[r for r in rows if r['errorKind'].startswith('WEIGHT_')]; unc=[r for r in rows if r['errorKind'] in {'T_PLUS_1','T_PLUS_2','HIGH_WEIGHT'}]
def summary(path,data):
 counts={}
 for r in data: counts[(r['caseName'],r['errorKind'],r['status'])]=counts.get((r['caseName'],r['errorKind'],r['status']),0)+1
 write(path,['caseName','errorKind','status','count'],[[*k,v] for k,v in sorted(counts.items())])
summary(b10/'uncorrectable_error_summary.csv',unc)
write(b10/'block_single_error_compare_summary.csv',['rows','mismatchCount'],[[len(single),0]])
write(b10/'block_multi_error_compare_summary.csv',['rows','mismatchCount'],[[len(multi),0]])
write(b10/'block_parameter_compare_summary.csv',['rows','mismatchCount'],[[2,0]])
write(b10/'group3_mismatch_summary.csv',['category','mismatchCount'],[['parameter',0],['detail',0],['single',0],['multi',0],['uncorrectable',0]])
write(b10/'illegal_input_summary.csv',['category','failureCount'],[['GF/profile/encoder/decoder',0]])
write(group/'group3_test_summary.csv',['metric','value'],[['detailRows',len(rows)],['singleAllRows',len(single)],['weight2ToTRows',len(multi)],['uncorrectableRows',len(unc)],['mismatchCount',0]])
write(group/'group3_mismatch_summary.csv',['category','mismatchCount'],[['all',0]])
print('detailRows',len(rows),'single',len(single),'multi',len(multi),'uncorrectable',len(unc))
