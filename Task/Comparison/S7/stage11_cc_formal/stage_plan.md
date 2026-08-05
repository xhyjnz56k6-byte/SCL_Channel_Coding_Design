# Stage11 CC Formal 计划

4 配置×558 组=2232 方案点。`SHORT D8` 与 `PSEUDO128` 标记为推荐工程配置对比；`SHORT D16` 与 `PSEUDO128` 标记为 `CC_EQUAL_SPAN_128`，只有后者允许受控方法差异解释。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 工程配置语义 | CSV/checker | role/group 完整 | 声称纯方法差异 | pureMethodDifferenceAllowed=false |
| 等跨度128 | D16 vs Pseudo128 | span 都为128 | D8 混入 | controlled group 恰两配置 |
| pair-stop | runner | 同组帧数 | 不同停止 | 558 组一致 |

