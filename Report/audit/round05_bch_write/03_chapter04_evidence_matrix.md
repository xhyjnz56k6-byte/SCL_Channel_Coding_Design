# 第4章证据矩阵

| 正文内容 | 主要证据 | 报告资产 | 结论边界 |
|---|---|---|---|
| 八个BCH方案 | S1正式results.csv、case adapter、block/segmented源码 | 参数表 | 只描述正式case |
| S1 AWGN | S1人工确认目录296行CSV与配置 | 4张可靠性图、1张时延图 | 0.5 dB网格、最多50000帧 |
| 固定多径 | common-SNR正式CSV与冻结tap | 1张双面板FER图 | 已知固定实数信道、MMSE |
| 相位漂移 | CFO formal CSV与0°至30°线性相位律 | 1张双面板FER图 | 无补偿，不称固定相位或多普勒 |
| 连续遮挡 | blockage formal的SNR实验 | 1张双面板FER图 | 约10%幅度置零、噪声保留 |
| 连续翻转 | burst formal summary | 1张双面板FER图 | 无AWGN、无交织 |
| 软件时延 | S1 decodeTime字段 | 正文时延图 | CPU测量，不代表硬件时延 |
