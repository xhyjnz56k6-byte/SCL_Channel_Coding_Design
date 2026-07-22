# BCH Group 4 commands

Primary one-stage commands are recorded in each Stage `commands_used.md`. Final regressions used:

```text
cmake --build Task/Common/build/stage04 --config Release -j 4
ctest --test-dir Task/Common/build/stage04 --output-on-failure
cmake --build Task/BCH/segmented/build/bch06_group3_final_regression --config Release -j 4
ctest --test-dir Task/BCH/segmented/build/bch06_group3_final_regression --output-on-failure
cmake --build Task/BCH/block/build/group3 --config Release -j 4
ctest --test-dir Task/BCH/block/build/group3 --output-on-failure
cmake --build Task/BCH/simulation/build/current --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure
python Task/BCH/segmented/scripts/run_bch06_segmented_matlab_reference.py --repo-root . --build-dir Task/BCH/segmented/build/bch06_group3_final_regression --matlab-command D:\Apps\Matlab\bin\matlab.exe
python Task/BCH/block/scripts/run_bch_group3.py --all --matlab-command D:\Apps\Matlab\bin\matlab.exe --build-dir Task/BCH/block/build/group3
```

One-command Stage reproduction:

```text
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch15 --progress --progress-refresh-seconds 1.0
python Task/BCH/simulation/scripts/run_bch_group4.py --stage bch16 --progress
```
