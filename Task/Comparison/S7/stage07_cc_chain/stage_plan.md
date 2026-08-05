# Stage07 CC 链路计划

LLR 解交织后进入现有 float soft Viterbi；tie 依次选择较小 predecessor 和 input 0；终止 traceback 从 state 0 开始。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 无噪声恢复 | runCcFrame | NONE/block/random | 先硬判 | payload 全等 |
| LLR 顺序 | deinterleaveValues | pair mapping | 解交织 bit | LLR 逆映射 |
| tie/traceback | Viterbi + MATLAB | 全零度量 | 不同 tie | trace 一致 |

