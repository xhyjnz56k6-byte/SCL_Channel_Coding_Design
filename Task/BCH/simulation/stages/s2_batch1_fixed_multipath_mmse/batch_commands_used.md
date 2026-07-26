# Commands Used

```text
git fetch origin
git diff --check
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure
python Task/BCH/simulation/scripts/compare_awgn_multipath.py
python Task/BCH/simulation/scripts/plot_bch_s2_multipath.py
python Task/BCH/simulation/scripts/check_bch_s2_batch1.py
```

Formal, MATLAB, S1 AWGN formal, frequency offset, erasure, and burst-error simulations were not rerun.
