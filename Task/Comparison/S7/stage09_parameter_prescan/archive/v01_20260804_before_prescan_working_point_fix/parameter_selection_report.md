# S7 Stage09 参数选择与 Formal 资源估算

原始预扫描：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\prescan_raw.csv`。候选排名：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\candidate_ranking.csv`。

评分越低越好；显式权重为平均 FER 0.40、六位置最坏 FER 0.30、缓冲比例 0.15、解交织 CPU 开销 0.15。另输出四目标 Pareto 标记。该排名是工程折中，不把不等跨度结果解释为纯方法差异。

- BCH 推荐候选：ROW_COLUMN，参数 15，排名 1，平均 FER=0.970833，最坏位置 FER=1（TAIL），bufferBits=285，平均解交织=236.667 ns。
- CC 推荐候选：SHORT_DEPTH_BLOCK，参数 4，排名 2，平均 FER=1，最坏位置 FER=1（HEAD），bufferBits=64，平均解交织=312.708 ns。

## Formal 矩阵

- 每个编码的比较组数：31×3×6=558。
- BCH 方案点数：2232；CC 方案点数：1674；合计 3906。
- 两类编码比较组合计：1116。
- 单线程估算：最少 1000 帧约 0.20 小时；按 5000 帧规划约 0.98 小时；50000 帧上限约 9.84 小时。
- 估算使用预扫描 decode+deinterleave 均值并乘 1.5 调度/信道/I/O 系数；正式运行前应以 Release runner 小批量基准校准。
- 最大磁盘估算约 770.5 MiB，假设每方案点 2 KiB 汇总且每 1000 帧 checkpoint 4 KiB；不保存逐帧 trace。

## Checkpoint 恢复

每 1000 帧保存 configHash、caseKey、nextFrameIndex、累计计数、计时样本和 frameSequenceHash。恢复时先验证配置 hash 与 case key，再从 nextFrameIndex 继续；合并 checker 必须证明无重复、无跳帧且恢复前后 frameSequenceHash 一致。

本报告只用于选择 Stage10 候选；Stage10 仍未授权。
