# Stage08：连续突发干扰

目标：5% 单段复高斯干扰、ISR=10 dB、未知 mask、nominal AWGN LLR、无交织。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 复总功率 ISR | `burstBeta` | beta=sqrt(5) | beta=sqrt(10) 拒绝 | MATLAB 公式通过 |
| 起点/长度 | `runChannel` | round(0.05N) | 回绕拒绝 | 相对起点确定性 |
| 未知 mask 接收机 | 同上 | nominal LLR | 擦除/bit flip/交织拒绝 | `PASS_S5_BURST` |

Gate：`PASS_S5_BURST`。
