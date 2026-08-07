# 横轴与图审计

| 数据 | 原始定义 | 报告横轴 | 处理 |
|---|---|---|---|
| S1 AWGN | `sigma2=10^(-snrDb/10)` | Es/N0 | `snrDb-10log10(2)` |
| S2固定多径 | `sigma2=10^(-waveformSnrDb/10)` | Es/N0 | `waveformSnrDb-10log10(2)` |
| S2相位漂移 | `sigma2=1/(2*10^(snrDb/10))` | Es/N0 | 原值 |
| S2遮挡 | `snrDb=ebn0Db+10log10(R)` | Es/N0 | 原值 |
| S2纯突发 | 无AWGN | 突发长度 | 不换算 |

报告图共9张：正文7张、附录2张。所有新图使用中文标题/坐标；BER/FER对数图省略原始值为0的点，不更改CSV中的0，不绘制error floor。每张图均由`Report/data/chapter04/bch`中的报告版CSV追溯到Task正式CSV。
