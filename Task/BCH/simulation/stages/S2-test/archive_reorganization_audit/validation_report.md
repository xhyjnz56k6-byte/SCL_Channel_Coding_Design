# Validation report

The relocation checks completed as follows:

- CMake configure: PASS;
- C++ Release build: PASS;
- CTest: PASS, 7/7;
- Python help, dry-run and AWGN/multipath comparison: PASS;
- Python syntax compilation: PASS;
- local result counts, byte totals and key SHA-256 checks: PASS;
- nonhistorical old-path reference scan: PASS, zero hits;
- MATLAB path check: PASS with two pre-existing format warnings.

The final archive Gate is currently **BLOCKED** because the migration is an
uncommitted working-tree change and has not been pushed for remote
verification. No claim of final PASS is made in this state.
