# Commands Used

```text
git fetch origin
git diff --check
cmake --build Task/BCH/simulation/build/S2-test --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/S2-test --output-on-failure
python Task/BCH/simulation/scripts/S2-test/compare/compare_awgn_multipath.py
python Task/BCH/simulation/scripts/S2-test/plot/plot_bch_s2_multipath.py
python Task/BCH/simulation/scripts/S2-test/check/check_bch_s2_batch1.py
```

Formal, MATLAB, S1 AWGN formal, frequency offset, erasure, and burst-error simulations were not rerun.
