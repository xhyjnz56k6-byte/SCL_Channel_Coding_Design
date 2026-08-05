# Stage03 BCH 交织器计划

实现四种冻结方法；CODEBLOCK depth=4/8/16/19，ROW_COLUMN rows=4/8/15/19，全帧伪随机固定 seed。等跨度方法比较与方法内参数敏感性分开记录。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 正逆映射 | s7.cpp | 全候选 round-trip | 重复/越界 | 逐 bit 一致 |
| 末组 | CODEBLOCK | D=4/8/16 | 非法 padding | 285 bit 不变 |
| 公平分组 | metadata | FULL_FRAME_285 | D=4 对全帧冒充纯方法差异 | span/buffer/group 齐全 |

