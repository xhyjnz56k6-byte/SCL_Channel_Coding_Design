# Stage09 参数预扫描计划

比较 BCH 10 个配置、CC 7 个配置；同组固定 50 帧，共享 payload/noise/burst/frame sequence。评分权重：区分组平均 FER 0.40、最坏位置 FER 0.30、buffer 0.15、deinterleave CPU 0.15；保留 Pareto 标记。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 公平性 | analyzer | 五类 hash/帧数 | 任一 mismatch | 同组完全一致 |
| 排名 | ranking/report | 四指标/Pareto | 单 FER/隐藏权重 | 权重和明细公开 |
| 两层比较 | report | 等跨度+内部参数 | 不等跨度冒充方法差异 | 分节输出 |
| Formal 估算 | report | 点数/组数/时间/磁盘/恢复 | 自动启动 | authorized=false |

