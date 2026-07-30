# stage09_bp_nms_pairing

## 目标

证明 BP、NMS 与全部 alpha 候选共享完全相同的信道 LLR。

## 非目标

不修改 CC/BCH/Common/旧工程；不使用速率匹配、分块、交织；不启动 formal。

## 范围

仅 `Task/LDPC/**`。

## 接口/数据格式

K=300，BG2 Direct，Es/N0，CSV/JSON/PNG UTF-8。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 证明 BP、NMS 与全部 alpha 候选共享完全相同的信道 LLR。 | `Task/LDPC/block` | Release build、unit/reference/smoke | 非满秩、NaN/Inf、依赖与哈希检查 | `PASS_STAGE09_BP_NMS_PAIRING` |

## Gate

PASS_STAGE09_BP_NMS_PAIRING
