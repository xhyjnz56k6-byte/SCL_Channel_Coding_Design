# stage01_legacy_code_audit

## 目标

只读审计旧参考工程的 Stage19、Stage23g-Rerun 与 Stage15b。

## 非目标

不修改 CC/BCH/Common/旧工程；不使用速率匹配、分块、交织；不启动 formal。

## 范围

仅 `Task/LDPC/**`。

## 接口/数据格式

K=300，BG2 Direct，Es/N0，CSV/JSON/PNG UTF-8。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 只读审计旧参考工程的 Stage19、Stage23g-Rerun 与 Stage15b。 | `Task/LDPC/block` | Release build、unit/reference/smoke | 非满秩、NaN/Inf、依赖与哈希检查 | `PASS_STAGE01_LEGACY_CODE_AUDIT` |

## Gate

PASS_STAGE01_LEGACY_CODE_AUDIT
