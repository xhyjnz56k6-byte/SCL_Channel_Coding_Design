# 密集波形 SNR 复现命令

```powershell
python Task/BCH/simulation/stages/S2/stage12_blockage_formal/python/stage12_blockage_formal_run.py
python Task/BCH/simulation/stages/S2/stage12_blockage_formal/python/stage12_blockage_formal_checker.py
python Task/BCH/simulation/stages/S2/stage12_blockage_formal/python/stage12_blockage_formal_matlab_spotcheck.py
```

实验 B 固定 10% 遮挡，正式网格为 `0.0:0.5:8.0 dB`，8 Case 共 136 点；实验 A 与 C 未重跑。
