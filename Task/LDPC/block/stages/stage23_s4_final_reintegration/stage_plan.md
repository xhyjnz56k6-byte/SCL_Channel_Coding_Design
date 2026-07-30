# stage23_s4_final_reintegration

## 目标

Reintegrate revised S4-LDPC formal results

## 非目标

不使用 rateMatch/rateRecover，不改变 alpha，不修改旧 Stage，不修改 Task/LDPC 外文件。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 正式冻结 | results/config | hash 与字段检查 | 错 alpha/SNR/停止参数 | 精确一致 |
| 配对公平 | point results | frames/seed/hash 一致 | 不同帧边界 | 无错配 |
| 安全恢复 | checkpoint | 中断恢复一致 | 配置/hash 不同 | 拒绝不兼容 |
| 数据可靠 | checker | 完整性与公式 | NaN/重复/缺失 | 全 PASS |
