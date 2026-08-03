# Stage04：固定多径

目标：单位能量三径 `[1,0.65,0.35]`、delay `[0,1,3]`，已知信道实轴线性 MMSE，逐符号 `gk/vk` 对角高斯近似 LLR。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| H 与卷积 | `runChannel` | 固定向量 | delay 越界 | MATLAB 一致 |
| 实轴 MMSE | `multipathReceiver` | SPD、有限输出 | 非正定拒绝 | A=(HᵀH+σ²I)⁻¹Hᵀ |
| gk/vk LLR | 同上 | g/v>0 | NaN/Inf 拒绝 | `PASS_S5_MULTIPATH` |

Gate：`PASS_S5_MULTIPATH`。
