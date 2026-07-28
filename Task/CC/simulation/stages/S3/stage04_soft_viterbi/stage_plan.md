# Stage04 浮点软判决 Viterbi 计划

目标是实现基于 `receivedSymbols` 的平方欧氏分支度量、64-state ACS、确定性 tie-break、逐步归一化和已知零终止完整回溯。

允许修改 `Task/CC/block/current/**` 与本 Stage；禁止其他编码目录。

| 需求 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|
| 欧氏软度量 | 无噪声及固定低噪声 100 帧 | NaN/Inf 拒绝 | payload mismatch=0 |
| hard/soft 公平输入 | 同一 receivedSymbols 派生 hardBits | 独立噪声禁止 | 共享链路 |
| MATLAB 对照 | `vitdec` terminated unquantized | mismatch 失败 | mismatch=0 |

Gate：`PASS_STAGE04_CC_SOFT_VITERBI`
