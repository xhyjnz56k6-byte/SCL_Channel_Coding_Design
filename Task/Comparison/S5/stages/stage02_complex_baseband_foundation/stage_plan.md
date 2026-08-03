# Stage02：复基带基础

目标：BPSK 复表示、Es/N0 噪声、`s5_complex_pair_v1` 在线 I/Q 独立高斯、有限无噪声软度量。Common-04 保持不变，不生成 50000 帧复噪声池。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| I/Q 在线噪声 | `complexNoise` | 1280 点可复现 | I=Q 拒绝 | policy/hash 稳定 |
| 无噪声软度量 | `finiteSoft` | ±100 | 除零拒绝 | 无 NaN/Inf |
| BPSK/EsN0 | `runChannel` | 定值公式 | 非有限 Es/N0 拒绝 | `PASS_S5_COMPLEX` |

Gate：`PASS_S5_COMPLEX`。
