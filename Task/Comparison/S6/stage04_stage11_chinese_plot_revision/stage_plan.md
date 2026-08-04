# Stage04 Stage11 中文重绘计划

## 范围

只读取 S5 Stage11 原图与 S5 Formal CSV；输出到 S6 新目录；不修改 S5 文件。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 86 图定位 | S5 stage11/plots | 数量与文件核验 | 缺文件阻断 | 恰好 86 |
| 源数据追溯 | plot_manifest + Formal CSV | SHA256 比对 | 哈希不符阻断 | 86/86 匹配 |
| 中文重绘 | replot_stage11.py | 标题和坐标检查 | 非中文标题阻断 | 86/86 通过 |
| 零值策略 | figure_data.csv | raw/plot/isPlotted 检查 | 对数轴绘零阻断 | 所有零值保留且不绘制 |
| 输出完整性 | 单图目录 | 4 个必需文件与哈希 | 缺失阻断 | 86/86 完整 |
