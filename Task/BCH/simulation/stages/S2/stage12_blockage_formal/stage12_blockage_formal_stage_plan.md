# stage12_blockage_formal 规格与 Gate

正式模型为符号层连续矩形遮挡，幅度 0、遮挡区保留 AWGN、逐帧随机起点、不回绕、不交织。
实验 A 在 K200/K300 公共锚点扫描 8 档比例；实验 B 固定 10% 遮挡扫描 5 档 Eb/N0。
每点停止规则为 5000/200/50000，绘图 SNR 逐 Case 按实际码率转换。

| 需求 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|
| 比例实验 | 64 点 | 区间越界 | 整数换算一致 |
| SNR 实验 | 40 点 | 错误横轴 | 逐 Case 公式一致 |
| 原始统计 | BER/FER/误纠/起点/区内外 | 超 50000 | 整数可复算 |
| 图与审计 | 10 PNG/data/manifest | PDF/伪零值 | SHA/PNG PASS |

Gate：`PASS_STAGE12_BLOCKAGE_FORMAL`。
