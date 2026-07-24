# Commands Used

```text
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure
python Task/BCH/simulation/scripts/audit_s1_awgn_baseline.py
python Task/BCH/simulation/scripts/run_bch_s2_batch1.py --stage s2-04 --formal-only --resume --no-progress
python Task/BCH/simulation/scripts/compare_awgn_multipath.py
python Task/BCH/simulation/scripts/plot_bch_s2_multipath.py
matlab -batch "run_bch_s2_multipath_reference(...)"
python Task/BCH/simulation/scripts/check_bch_s2_batch1.py
```
