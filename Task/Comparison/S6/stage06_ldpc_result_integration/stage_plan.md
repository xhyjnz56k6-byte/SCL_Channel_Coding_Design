# Stage06 LDPC N560 整合计划

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| N560 元数据 | Stage23 Formal | N/Zc/filler/rank | 非 N560 排除 | 62 行 |
| BP/NMS 配对 | payload/codeword/LLR hash | 31 对哈希相同 | 任一 mismatch 阻断 | 31/31 |
| 迭代配置 | maxIterations/earlyStop | 32 + syndrome | 非 32 排除 | 唯一值正确 |
| NMS 参数 | alpha | 0.95 | 其他 alpha 排除 | 31 行 |
| 指标完整性 | 复杂度/存储/时延 | 有限非负 | NaN/Inf 阻断 | 所有字段有效 |
