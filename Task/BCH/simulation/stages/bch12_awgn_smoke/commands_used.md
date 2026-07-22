# BCH-12 commands

```text
cmake -S Task/BCH/simulation/current -B Task/BCH/simulation/build/current -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ...
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure -R "bch11|bch12"
python Task/BCH/simulation/scripts/run_bch_group4.py --dry-run --no-progress
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch12 --progress --progress-refresh-seconds 0.2
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch12 --no-progress --progress-refresh-seconds 0.2
python Task/BCH/simulation/scripts/plot_bch_smoke.py --summary Task/BCH/simulation/results/smoke/awgn_smoke_summary.csv --output-dir Task/BCH/simulation/results/smoke
python Task/BCH/simulation/scripts/audit_bch_group4.py --stage bch12 --results-dir Task/BCH/simulation/results/smoke --stage-dir Task/BCH/simulation/stages/bch12_awgn_smoke
```
