# stage10_cfo_formal 规格与 Gate

目标：固定整帧累计 30°、无补偿、实部硬判决，按 K200/K300 公共 Eb/N0 网格完成正式性能实验。
非目标：角度扫描、CFO 估计/补偿。正式点停止规则为 5000/200/50000，横轴逐 Case 换算为
`snrDb=ebn0Db+10log10(actualRate)`。

| 需求 | 实现 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 30° formal | C++ runner | 40 点整数统计 | CLI/模式拒绝 | 帧数≤50000 |
| trial 冻结 | results/trial | 24 点×500 帧 | 不混入 formal | 明确 TRIAL |
| 科研绘图 | Python | 8 PNG+figure-data | 禁 PDF/伪零值 | SHA 可复算 |
| 结果审计 | checker | BER/FER/SNR/相位复算 | NaN/Inf | 全部一致 |

Gate：`PASS_STAGE10_CFO_FORMAL`。
