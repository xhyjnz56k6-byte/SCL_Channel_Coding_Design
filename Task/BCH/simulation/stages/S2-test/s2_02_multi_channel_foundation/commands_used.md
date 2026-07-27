# Commands Used

```text
cmake --build Task/BCH/simulation/build/S2-test --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/S2-test --output-on-failure
python Task/BCH/simulation/scripts/audit_s1_awgn_baseline.py
python Task/BCH/simulation/scripts/S2-test/run/run_bch_s2_batch1.py --stage s2-04 --formal-only --resume --no-progress
python Task/BCH/simulation/scripts/S2-test/compare/compare_awgn_multipath.py
python Task/BCH/simulation/scripts/S2-test/plot/plot_bch_s2_multipath.py
matlab -batch "run_bch_s2_multipath_reference(...)"
python Task/BCH/simulation/scripts/S2-test/check/check_bch_s2_batch1.py
```
