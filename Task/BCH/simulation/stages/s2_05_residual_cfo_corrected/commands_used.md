# Commands used

```text
python Task/BCH/simulation/scripts/run_bch_s2_scientific_correction.py --resume
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current -C Release --output-on-failure -R bch_s2_impairments_unit
python Task/BCH/simulation/scripts/check_bch_s2_corrected.py
```
