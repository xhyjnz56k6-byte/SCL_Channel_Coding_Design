# Stage05 MATLAB 官方参考计划

目标是以 `poly2trellis`、`convenc`、`vitdec` 对 C++ trellis、编码、终止、hard/soft、receivedSymbols/LLR 和 bit order 做逐 bit 独立验证。

范围仅为本 Stage，复用 Stage02～04 冻结实现；禁止修改其他编码目录。

| 需求 | 正向测试 | 负向条件 | Gate |
|---|---|---|---|
| 完整 trellis | 128 分支逐项比较 | 任一 next/output mismatch | mismatch=0 |
| 编码/尾/状态 | 16 个 300-bit 向量 | 位序或路序错误 | mismatch=0 |
| hard/soft/LLR | 同一固定接收值 | 符号约定错误 | payload mismatch=0 |
| reference hash | 三个资产 SHA256 | 文件变化 | hash 可复算 |

Gate：`PASS_STAGE05_CC_MATLAB_REFERENCE`
