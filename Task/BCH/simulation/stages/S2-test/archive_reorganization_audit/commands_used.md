# Commands used

```text
python Task/BCH/simulation/scripts/S2-test/check/scan_s2_ownership.py
cmake --fresh -G "MinGW Makefiles" -S Task/BCH/simulation/current -B Task/BCH/simulation/build/S2-test -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/build/S2-test --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/S2-test --output-on-failure
python Task/BCH/simulation/scripts/S2-test/run/run_bch_s2_batch1.py --help
python Task/BCH/simulation/scripts/S2-test/run/run_bch_s2_batch1.py --dry-run --stage s2-04
python Task/BCH/simulation/scripts/S2-test/compare/compare_awgn_multipath.py
python -m py_compile Task/BCH/simulation/scripts/S2-test/**/*.py
matlab -batch "checkcode('Task/BCH/simulation/matlab_official_validation/S2-test/matlab/run_bch_s2_multipath_reference.m')"
```
