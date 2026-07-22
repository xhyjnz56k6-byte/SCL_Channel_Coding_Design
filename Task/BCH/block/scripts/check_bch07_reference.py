import csv
import sys

def rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))

if len(sys.argv) != 3:
    raise SystemExit('usage: check_bch07_reference.py cpp.csv matlab.csv')
cpp, matlab = rows(sys.argv[1]), rows(sys.argv[2])
if cpp != matlab:
    raise SystemExit('BLOCKED_BCH07_GF_CPP_MATLAB_MISMATCH')
if len(cpp) != 2 or {row['caseName'] for row in cpp} != {'BCH-B200', 'BCH-B300'}:
    raise SystemExit('profile rows invalid')
print('PASS_BCH07_CPP_MATLAB_PARAMETER_REFERENCE')
