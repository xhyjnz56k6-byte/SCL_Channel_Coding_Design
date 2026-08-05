# Stage13 计划

目标：汇总 T_decode、T_interleave_cpu、T_deinterleave_cpu、T_add_cpu、bufferBits、startupDelayBits、startupDelayTrellisSteps 和 bufferFractionOfFrame。

非目标：不伪造物理时间，不重新运行 Formal，不把 CC 不同跨度解释为纯方法差异。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| CPU 汇总 | `analyze_stage13.py` | frames 加权均值 | T_add 不等于两项之和 | 八配置完整且恒等式成立 |
| 结构代价 | 汇总 CSV | buffer/span 映射 | D8 写成 128 step | D8=64，D16/Pseudo=128 |
| 语义限制 | checker | physicalLatencyClaimAllowed=false | 换算物理时间 | 不出现物理时延结论 |
