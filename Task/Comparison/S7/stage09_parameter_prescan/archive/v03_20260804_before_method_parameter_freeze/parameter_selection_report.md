# S7 Stage09 参数选择与 Formal 资源估算

原始预扫描：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\prescan_raw.csv`。候选排名：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage09_parameter_prescan\results\candidate_ranking.csv`。

共 72 个比较组，其中 36 个组的候选 FER 存在差异并用于排名；所有饱和组仍保留在原始 CSV 和 overallMeanFer。评分越低越好；显式权重为区分组平均 FER 0.40、区分组六位置最坏 FER 0.30、缓冲比例 0.15、解交织 CPU 开销 0.15。另输出四目标 Pareto 标记。该排名是工程折中，不把不等跨度结果解释为纯方法差异。

- BCH 推荐候选：BCH_CODEBLOCK，参数 19，排名 1，平均 FER=0.440278，最坏位置 FER=0.466667（TAIL），bufferBits=285，平均解交织=247.778 ns。
- CC 推荐候选：SHORT_DEPTH_BLOCK，参数 8，排名 1，平均 FER=0.677778，最坏位置 FER=0.9（THREE_QUARTER），bufferBits=128，平均解交织=442.315 ns。

## 等跨度方法公平对比

- BCH / FULL_FRAME_285：BCH_CODEBLOCK:参数 19, FER=0.440278, buffer=285；GLOBAL_PSEUDORANDOM:参数 285, FER=0.797222, buffer=285；ROW_COLUMN:参数 15, FER=0.401389, buffer=285。
- CC / TRELLIS_SPAN_128：PSEUDORANDOM:参数 128, FER=0.552778, buffer=256；SHORT_DEPTH_BLOCK:参数 16, FER=0.822222, buffer=256。
- CC / TRELLIS_SPAN_32：PSEUDORANDOM:参数 32, FER=0.994444, buffer=64；SHORT_DEPTH_BLOCK:参数 4, FER=0.997222, buffer=64。
- CC / TRELLIS_SPAN_64：PSEUDORANDOM:参数 64, FER=0.877778, buffer=128；SHORT_DEPTH_BLOCK:参数 8, FER=0.677778, buffer=128。

## 方法内部参数敏感性

完整排名 CSV 保留同一 method 的全部参数；选择报告不把不同 span 的差异解释为纯方法差异。BCH 分别扫描 CODEBLOCK depth 与 ROW_COLUMN rows；CC 分别扫描 SHORT_DEPTH depth 与 PSEUDORANDOM span。

## Formal 矩阵

- 每个编码的比较组数：31×3×6=558。
- BCH 方案点数：2232；CC 方案点数：1674；合计 3906。
- 两类编码比较组合计：1116。
- 单线程估算：最少 1000 帧约 0.26 小时；按 5000 帧规划约 1.28 小时；50000 帧上限约 12.81 小时。
- 估算使用预扫描 decode+deinterleave 均值并乘 1.5 调度/信道/I/O 系数；正式运行前应以 Release runner 小批量基准校准。
- 最大磁盘估算约 770.5 MiB，假设每方案点 2 KiB 汇总且每 1000 帧 checkpoint 4 KiB；不保存逐帧 trace。

## Checkpoint 恢复

每 1000 帧保存 configHash、caseKey、nextFrameIndex、累计计数、计时样本和 frameSequenceHash。恢复时先验证配置 hash 与 case key，再从 nextFrameIndex 继续；合并 checker 必须证明无重复、无跳帧且恢复前后 frameSequenceHash 一致。

本报告只用于选择 Stage10 候选；Stage10 仍未授权。
