# BCH-11 changed files

The functional range adds the unified BCH simulation adapter and its CMake/test integration, plus
the BCH-11 and Group 4 frozen plans. Generated BCH-11 evidence and audit records are added after the
functional commit and are not part of the audited functional range.

The later `orderedRunnerRepair` range changes only `run_bch_group4.py` so `--stage bch11` and
`--all` actually build and execute the required BCH-11 CTest before subsequent stages.
