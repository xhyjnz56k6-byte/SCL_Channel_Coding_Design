# Stage12 命令

```powershell
python Task\Comparison\S7\scripts\select_stage12_workpoints.py Task\Comparison\S7\stage12_all_start_scan\selected_workpoints.json
Task\Comparison\S7\build\stage10_formal\s7_all_start_runner.exe BCH Task\Comparison\S7\stage12_all_start_scan\results\bch -5 5.5 10
Task\Comparison\S7\build\stage10_formal\s7_all_start_runner.exe CC Task\Comparison\S7\stage12_all_start_scan\results\cc -5 -3 10
python Task\Comparison\S7\scripts\check_stage12.py
python Task\Comparison\S7\scripts\analyze_stage12.py
```

另以 `--group-limit 2` 后 `--group-limit 4` 对 BCH/CC 分别执行恢复预检。

2026-08-05 BCH 2%补扫：

```powershell
Task\Comparison\S7\build\stage10_formal\s7_all_start_runner.exe BCH Task\Comparison\S7\stage12_all_start_scan\results\bch_2_percent -5 5.5 10 --ratio 0.02
python Task\Comparison\S7\scripts\check_stage12.py
```
