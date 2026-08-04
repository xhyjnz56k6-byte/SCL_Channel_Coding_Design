# Stage02 BCH 复杂度与存储埋点

目标、接口与 Gate 继承 Stage01。计数按 syndrome、BM、Chien、修正/复核分区；存储采用 `EXACT_FROM_TYPE_AND_COUNT`，包含对象类型、vector capacity 对应元素字节及工作缓冲，不声称包含分配器隐藏开销。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| S200 计数 | segmented current | 2048消息、19单错 | 零 syndrome 不 lookup | PASS_BCH_COUNTER_UNIT_TESTS |
| B200 计数 | block current | 0~6错 | 非法输入沿用既有测试 | PASS_BCH_COUNTER_UNIT_TESTS |
| 存储 | 两类适配器 | 值与方法合法 | 0/方法缺失失败 | PASS_BCH_MEMORY_ACCOUNTING |
| 行为一致 | 既有全套 BCH 测试 | 全回归 | 任一 mismatch 停止 | PASS_BCH_COUNTER_UNIT_TESTS |
