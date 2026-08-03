# Stage07：短时遮挡

目标：10% 单段不回绕遮挡，理想已知 mask，遮挡区 LLR 精确为 0，无交织。结论仅限已知连续擦除场景。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 相对起点与长度 | `runChannel` | round(0.1N) | 越界/回绕 | mask 数量精确 |
| 已知擦除 LLR | 同上 | blocked LLR=0 | nominal LLR 混入 | `PASS_S5_BLOCKAGE` |

Gate：`PASS_S5_BLOCKAGE`。
