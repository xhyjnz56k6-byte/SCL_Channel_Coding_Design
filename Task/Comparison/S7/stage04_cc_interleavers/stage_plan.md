# Stage04 CC 交织器计划

冻结 `permutationUnit=TRELLIS_STEP`、`preserveMotherOutputPair=true`。短深度窗口为 D×8 steps；伪随机局部 span 为 32/64/128 steps。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 输出对保持 | s7.cpp | 每偶数输出索引检查 | span=31/拆 pair | pair 全保持 |
| 正逆映射 | unit test | 全候选 | 非法参数 | 612 bit 精确恢复 |
| 尾窗口 | step mapping | 306 余数 | 丢失/重复 | 306 steps 唯一 |

