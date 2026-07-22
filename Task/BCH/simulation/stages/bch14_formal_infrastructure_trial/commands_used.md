# BCH-14 commands

```text
cmake -S Task/Common -B Task/Common/build/stage04 -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build Task/Common/build/stage04 --config Release -j 4
ctest --test-dir Task/Common/build/stage04 --output-on-failure
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure -R "bch11|bch12"
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch14 --progress --progress-refresh-seconds 0.5
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch14 --no-progress --progress-refresh-seconds 0.5
python Task/BCH/simulation/scripts/audit_bch_group4.py --stage bch14 --results-dir Task/BCH/simulation/results/formal_trial --stage-dir Task/BCH/simulation/stages/bch14_formal_infrastructure_trial
```
