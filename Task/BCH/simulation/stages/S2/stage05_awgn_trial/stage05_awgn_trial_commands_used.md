# stage05_awgn_trial 命令

```powershell
python Task/BCH/simulation/stages/S2/stage05_awgn_trial/python/stage05_awgn_trial_run.py
python Task/BCH/simulation/stages/S2/stage05_awgn_trial/python/stage05_awgn_trial_audit.py
```

驱动脚本内部顺序执行 CMake configure/build、CTest、C++ 试运行、PNG 绘图和业务 checker。
