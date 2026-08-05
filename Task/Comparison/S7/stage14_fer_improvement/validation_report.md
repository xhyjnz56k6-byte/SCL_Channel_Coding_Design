# Stage14 验证报告

- FER 改善：744 行，基线匹配和绝对/相对公式 PASS。
- 位置敏感度：worst-best 恒等式 PASS。
- 目标 FER=0.5：24 行；基线均未唯一包围目标，Es/N0 gain 留空，未伪造数值。
- 突发容限：8 行；BCH 两配置在测试网格内满足阈值，其余明确标记低于最小测试 2%；不向网格外外推。
- 排名：BCH/CC 各 3 候选，公开权重和为 1，Pareto 标记完整。
- BCH 推荐：BCH_ROW_COLUMN_R15。
- CC 推荐：CC_PSEUDO_128_RECOMMENDED。
- CC 语义：D8/PSEUDO128 工程配置对比；D16/PSEUDO128 等跨度 128 受控对比，PASS。

Gate：PASS_STAGE14_FER_IMPROVEMENT。
