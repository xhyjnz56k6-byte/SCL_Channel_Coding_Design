import csv
import sys

def read(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))

if len(sys.argv) != 3:
    raise SystemExit('usage: check_bch10_detail.py cpp.csv matlab.csv')
cpp, matlab = read(sys.argv[1]), read(sys.argv[2])
if len(cpp) != 2912 or len(matlab) != 2912:
    raise SystemExit('BLOCKED_BCH10_REFERENCE_ROW_COUNT')
for index, (left, right) in enumerate(zip(cpp, matlab)):
    if left != right:
        differing = [key for key in left if left[key] != right.get(key)]
        raise SystemExit('BLOCKED_BCH10_CROSS_LANGUAGE_MISMATCH row=%d fields=%s' % (index, ':'.join(differing)))
if any(row['errorKind'] in {'NONE','FIRST','LAST','T'} and row['decodedPayload'] != row['payload'] for row in cpp):
    raise SystemExit('BLOCKED_BCH10_CORRECTABLE_PAYLOAD_MISMATCH')
print('PASS_BCH10_CPP_MATLAB_DETAIL_REFERENCE')
