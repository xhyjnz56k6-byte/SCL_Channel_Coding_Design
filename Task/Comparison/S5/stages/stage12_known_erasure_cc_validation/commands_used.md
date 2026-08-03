# 实际命令

```text
cmake -S Task/Comparison/S5 -B Task/Comparison/S5/build
cmake --build Task/Comparison/S5/build --config Release --target s5_stage12_cc_validation
Task/Comparison/S5/build/s5_stage12_cc_validation.exe Task/Comparison/S5/stages/stage12_known_erasure_cc_validation
matlab -batch "run_stage12_matlab(...)"
python Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/scripts/check_stage12.py
python Task/Comparison/S5/current/scripts/stage11_analysis.py
python Task/Comparison/S5/current/scripts/stage12_aggregate_plots.py
```
