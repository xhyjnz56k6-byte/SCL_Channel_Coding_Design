# 密集波形 SNR 复现命令

```powershell
python Task/BCH/simulation/stages/S2/stage10_cfo_formal/python/stage10_cfo_formal_run.py
python Task/BCH/simulation/stages/S2/stage10_cfo_formal/python/stage10_cfo_formal_checker.py
python Task/BCH/simulation/stages/S2/stage10_cfo_formal/python/stage10_cfo_formal_matlab_spotcheck.py
```

正式网格为 `0.0:0.5:8.0 dB`，8 Case 共 136 点；停止规则为 1000/200/50000 帧。
