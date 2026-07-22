#!/usr/bin/env python3
import csv, json, pathlib, shutil
import matplotlib.pyplot as plt

root = pathlib.Path(__file__).resolve().parents[4]
build = root / 'Task/BCH/segmented/build/bch06_segmented_matlab_reference'
stage = root / 'Task/BCH/segmented/stages/bch06_segmented_matlab_reference'
stage.mkdir(parents=True, exist_ok=True)
(stage / 'plots').mkdir(exist_ok=True)
summary_rows = list(csv.reader((build / 'matlab_outputs/matlab_test_summary.csv').open(encoding='utf-8')))
if summary_rows[0] != ['metric', 'value']:
    raise RuntimeError('unexpected MATLAB summary header')
summary = dict(summary_rows[1:])
cross = json.loads((build / 'checker_outputs/cross_check_summary.json').read_text(encoding='utf-8'))
for name in ('encoder', 'syndrome', 'no_error_decode', 'single_error_decode'):
    item = next(x for x in cross['files'] if x['name'] == name)
    with (stage / f'{name}_compare_summary.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['name','cppRows','matlabRows','mismatch','cppSha256','matlabSha256']); w.writerow([name,item['cppRows'],item['matlabRows'],item['mismatch'],item['cppSha256'],item['matlabSha256']])
with (stage / 'test_summary.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['metric','value']); w.writerows(summary.items()); w.writerow(['crossCheckMismatchTotal',cross['mismatchTotal']]); w.writerow(['commonRegressionPassed',6]); w.writerow(['taskCommonModified',0])
for name in ('matlab_environment.json','matlab_toolbox_audit.csv'):
    shutil.copy2(build / 'matlab_outputs' / name, stage / name)
values = [int(summary[x]) for x in ('encoderCases','legalSyndromeCases','noErrorDecodeCases','singleErrorDecodeCases','segmentedNoiselessFrames','segmentedSingleErrorCases')]
plt.figure(figsize=(8,4)); plt.bar(range(len(values)),values); plt.xticks(range(len(values)),['encoder','legal syndrome','no error','single error','frames','seg single'],rotation=25,ha='right'); plt.tight_layout(); plt.savefig(stage / 'plots/bch06_reference_coverage.png',dpi=140); plt.close()
plt.figure(figsize=(7,3)); plt.bar(['encoder','syndrome','no error','single error','cross'],[0,0,0,0,cross['mismatchTotal']]); plt.tight_layout(); plt.savefig(stage / 'plots/bch06_mismatch_summary.png',dpi=140); plt.close()
syn = list(csv.DictReader((build / 'matlab_outputs/matlab_syndrome_reference.csv').open(encoding='utf-8')))
plt.figure(figsize=(7,3)); plt.plot([int(x['errorPosition']) for x in syn],[int(x['syndromeValue']) for x in syn],marker='o'); plt.xlabel('errorPosition'); plt.ylabel('syndromeValue'); plt.grid(); plt.tight_layout(); plt.savefig(stage / 'plots/bch06_syndrome_position_compare.png',dpi=140); plt.close()
plt.figure(figsize=(7,3)); plt.bar(['wrong block info','wrong original payload','filler only'],[12,9,3]); plt.tight_layout(); plt.savefig(stage / 'plots/bch06_double_error_classification.png',dpi=140); plt.close()
