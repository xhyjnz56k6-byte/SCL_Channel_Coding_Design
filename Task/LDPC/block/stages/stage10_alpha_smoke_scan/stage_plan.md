# stage10_alpha_smoke_scan

## 目标

定位各实际码长 waterfall 并执行 alpha 粗搜索。

## 非目标

不修改 CC/BCH/Common/旧工程；不使用速率匹配、分块、交织；不启动 formal。

## 范围

仅 `Task/LDPC/**`。

## 接口/数据格式

K=300，BG2 Direct，Es/N0，CSV/JSON/PNG UTF-8。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 定位各实际码长 waterfall 并执行 alpha 粗搜索。 | `Task/LDPC/block` | Release build、unit/reference/smoke | 非满秩、NaN/Inf、依赖与哈希检查 | `PASS_STAGE10_ALPHA_SMOKE_SCAN` |

## Gate

PASS_STAGE10_ALPHA_SMOKE_SCAN
