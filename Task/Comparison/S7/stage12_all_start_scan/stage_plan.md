# Stage12 计划

目标：从 Formal 自动选择低、waterfall、高工作点，在 5%/10% 突发下遍历全部合法起点，并输出逐起点及聚合统计。

非目标：不对全部 31 个 SNR 做全起点遍历，不改变编码器、译码器、交织器或主信道定义，不生成最终推荐结论。

范围：仅 `Task/Comparison/S7/**`。输入为 Stage10/11 原始 Formal CSV。

数据格式：每个 scheme/config/workpoint/ratio/start 一行，记录 200 帧的 BER/FER、共享序列哈希、映射哈希和配置哈希。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 自动选择三工作点 | `select_stage12_workpoints.py` | 输入完整 Formal CSV | 缺点或非递增点 | LOW < WATERFALL < HIGH |
| 全起点遍历 | `s7_all_start_runner` | `0..N-L` 完整 | 缺失、重复、越界 | 起点集合精确相等 |
| 公平性 | runner/checker | 同组共享帧与噪声 | 哈希或帧数不同 | 四配置共享字段一致 |
| 可恢复 | CSV+checkpoint | 中断后继续 | 半组 CSV | 不重复、不跳组 |
| 聚合输出 | `analyze_stage12.py` | mean/worst/best 等 | 行数或范围错误 | 24 行/码并可回溯原始行 |

Gate：CMake/CTest PASS；恢复预检 PASS；BCH 6348 行、CC 13608 行；checker 与汇总 PASS。
