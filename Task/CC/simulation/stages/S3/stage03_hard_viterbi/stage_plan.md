# Stage03 硬判决 Viterbi 计划

## 目标与范围

实现 64 状态整块、已知零终止的硬判决 Viterbi。允许修改 `Task/CC/block/current/**` 与本 Stage；禁止修改其他编码目录。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 汉明度量和 64-state ACS | `hard_viterbi.cpp` | 无噪声与固定错误 | 非二进制拒绝 | payload 正确 |
| tie-break 和逐步归一化 | decoder/result | 重复运行与 tie 计数 | 无可达路径报错 | 确定性一致 |
| 零状态回溯和去尾 | decoder | 306→300 | 长度错误拒绝 | tail 正确 |
| MATLAB hard `vitdec` | MATLAB/CSV | 5 固定接收向量 | mismatch 触发失败 | mismatch=0 |

## Gate

`PASS_STAGE03_CC_HARD_VITERBI`
