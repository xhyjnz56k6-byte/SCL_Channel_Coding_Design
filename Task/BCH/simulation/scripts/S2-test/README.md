# BCH S2-test scripts

Scripts are grouped by purpose:

- `run/`: S2 batch drivers;
- `check/`: evidence and Gate checks;
- `compare/`: AWGN/multipath comparisons;
- `plot/`: audited figure generation;
- `finalize/`: Stage audit closure.

All scripts derive the repository root from their own location and are
intended to be invoked from the repository root. They use the S2-test
locations for code, build, stages, results, and MATLAB reference files.

The existing AWGN baseline audit remains shared with S1 and stays at
`Task/BCH/simulation/scripts/audit_s1_awgn_baseline.py`.
