# Stage01 范围与 schema 冻结

仅允许修改 `Task/Comparison/S7/**`。结果行至少记录 scheme、method、parameter、fairnessGroupId、spanBits、bufferBits、EsN0Db、sigmaSquared、burstRatioRequested/Actual、burstStart/End、position、frame counts、bit/frame errors、BER/FER、共享量 checksum、mapping hash、计时和 checkpoint 状态。

资产 Gate：覆盖前归档；每目录 readme；每图独立目录；原始与历史数据绝对路径；figure-data/manifest/validation/SHA256 齐全。

零值 Gate：原始 0 保留；对数图不画；不使用伪小值；不延伸水平线；不显示 error floor 或零错上界标记；零后非零阻止发布。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 写入边界 | checker | 仅 S7 diff | 其他目录变更 | 无越界文件 |
| schema | 配置/checker | 必需字段齐全 | 缺字段/NaN/Inf | 全行合法 |
| 零值 | 配置/plot checker | raw=0 plotted=false | 伪值或水平线 | 零值策略全通过 |
| 资产 | checker | readme/hash/绝对路径 | 覆盖、缺文件 | 资产完整 |

