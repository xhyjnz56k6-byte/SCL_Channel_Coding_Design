# Stage12R 全 α 曲线重选

## 目标

用 FER、平均译码时延和每帧 edge-message updates 三类曲线重新冻结各码长 α。

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
