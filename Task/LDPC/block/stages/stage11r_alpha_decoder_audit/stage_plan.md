# Stage11R α 与译码器行为专项审计

## 目标

审计 α=1.00 的 MS 语义、early-stop、错误合法码字、逐帧一致性和汇总隔离。

## 非目标

不启动 formal，不修改旧 Stage 结果，不修改 `Task/LDPC/` 之外的内容。

## 接口与数据

- 输入：冻结的 N480/N560/N640、共享 payload/noise、Es/N0、最大迭代 32。
- 输出：逐点 CSV、可追溯 figure-data/manifest/check、结论报告。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 同源输入 | `results/*.csv` 的输入 hash/seed | 同帧 hash 一致 | 候选隔离检查 | 无错配 |
| 译码与统计 | `current/` 与结果 CSV | build/unit/checker | NaN/Inf、四分类和边界检查 | 全部 PASS |
| 可追溯结果 | `results/` | figure-data 与 manifest 检查 | 缺文件检查 | 文件齐全 |

## Gate

所有真实执行的检查 PASS，且未发现需要越界修改的核心逻辑错误。
