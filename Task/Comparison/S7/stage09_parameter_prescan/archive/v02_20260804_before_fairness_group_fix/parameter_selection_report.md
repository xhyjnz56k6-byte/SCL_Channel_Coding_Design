# S7 Stage09 参数选择与 Formal 资源估算

原始预扫描：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\prescan_raw.csv`。候选排名：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\candidate_ranking.csv`。

共 72 个比较组，其中 36 个组的候选 FER 存在差异并用于排名；所有饱和组仍保留在原始 CSV 和 overallMeanFer。评分越低越好；显式权重为区分组平均 FER 0.40、区分组六位置最坏 FER 0.30、缓冲比例 0.15、解交织 CPU 开销 0.15。另输出四目标 Pareto 标记。该排名是工程折中，不把不等跨度结果解释为纯方法差异。

- BCH 推荐候选：ROW_COLUMN，参数 15，排名 1，平均 FER=0.401389，最坏位置 FER=0.475（MIDDLE），bufferBits=285，平均解交织=288.796 ns。
- CC 推荐候选：PSEUDORANDOM，参数 128，排名 1，平均 FER=0.552778，最坏位置 FER=0.933333（TAIL），bufferBits=256，平均解交织=310.185 ns。

## Formal 矩阵

- 每个编码的比较组数：31×3×6=558。
- BCH 方案点数：2232；CC 方案点数：1674；合计 3906。
- 两类编码比较组合计：1116。
- 单线程估算：最少 1000 帧约 0.20 小时；按 5000 帧规划约 1.00 小时；50000 帧上限约 10.00 小时。
- 估算使用预扫描 decode+deinterleave 均值并乘 1.5 调度/信道/I/O 系数；正式运行前应以 Release runner 小批量基准校准。
- 最大磁盘估算约 770.5 MiB，假设每方案点 2 KiB 汇总且每 1000 帧 checkpoint 4 KiB；不保存逐帧 trace。

## Checkpoint 恢复

每 1000 帧保存 configHash、caseKey、nextFrameIndex、累计计数、计时样本和 frameSequenceHash。恢复时先验证配置 hash 与 case key，再从 nextFrameIndex 继续；合并 checker 必须证明无重复、无跳帧且恢复前后 frameSequenceHash 一致。

本报告只用于选择 Stage10 候选；Stage10 仍未授权。
