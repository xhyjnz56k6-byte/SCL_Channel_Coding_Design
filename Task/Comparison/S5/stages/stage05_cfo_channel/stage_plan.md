# Stage05：CFO

目标：单帧相位从 0° 线性累计到 30°，不估计、不补偿，按实轴投影生成 nominal AWGN LLR。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 相位端点 | `runChannel` | 四种 Ntx 首末点 | 度/弧度错误 | 0°/30° 精确 |
| 复旋转 | MATLAB reference | 逐元素复算 | Ntx 分母错误 | `PASS_S5_CFO` |

Gate：`PASS_S5_CFO`。
