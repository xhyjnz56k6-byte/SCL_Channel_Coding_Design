# stage05_direct_encoder_matrix

## 目标

验证 Direct H/Hu/Hp 构造、GF(2) 编码和 payload/filler 映射。

## 非目标

不修改 CC/BCH/Common/旧工程；不使用速率匹配、分块、交织；不启动 formal。

## 范围

仅 `Task/LDPC/**`。

## 接口/数据格式

K=300，BG2 Direct，Es/N0，CSV/JSON/PNG UTF-8。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 验证 Direct H/Hu/Hp 构造、GF(2) 编码和 payload/filler 映射。 | `Task/LDPC/block` | Release build、unit/reference/smoke | 非满秩、NaN/Inf、依赖与哈希检查 | `PASS_STAGE05_DIRECT_ENCODER_MATRIX` |

## Gate

PASS_STAGE05_DIRECT_ENCODER_MATRIX
