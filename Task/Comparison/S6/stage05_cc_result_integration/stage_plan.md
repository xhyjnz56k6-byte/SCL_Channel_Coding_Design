# Stage05 CC 结果整合计划

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 整块 Hard/Soft | Stage14 Formal | 两方案各 31 点 | 量化方案排除 | 62 行 |
| 时隙 Hard/Soft | Stage14 Formal | B/C/D 各两方案 | 非 D70/W128/S25 排除 | 186 行 |
| 复杂度与存储 | ACS/traceback/memory | 非负有限 | 缺字段阻断 | 字段完整 |
| 两类时延分离 | CPU 与 symbols 字段 | 字段分类检查 | 混列阻断 | 明确分列 |
| 来源追溯 | source inventory | SHA256 | 哈希缺失阻断 | 单一源哈希有效 |
