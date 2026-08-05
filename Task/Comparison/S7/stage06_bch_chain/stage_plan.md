# Stage06 BCH 链路计划

解码计时从解交织硬 bit 完成后开始，到 payload 返回结束；不含硬判和解交织。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 无噪声恢复 | runBchFrame | 四种方法 | 错误 mapping | 200 bit 全等 |
| 原块边界 | decoder input | 19×15 | 交织边界直接译码 | 解交织后译码 |
| 计时范围 | DecodeTiming | 独立字段 | 混入解交织 | decode/deinterleave 分离 |

