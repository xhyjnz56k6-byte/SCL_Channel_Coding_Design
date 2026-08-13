# 正式数据来源

- 参数与 codec：`Task/BCH/simulation/current/src/bch_case_adapter.cpp`、`Task/BCH/segmented/current`、`Task/BCH/block/current`。
- S1 五方案主数据：`Report/data/frozen/bch/s1_01_five_case_formal_summary.csv`；源头为 BCH16W8。
- S1 Es/N0 图源与修复后时延：BCH16W9 `figures/*figure_data*.csv`、`timing_point_summary.csv`、`result_summary.csv`。
- S2 AWGN：Stage07 `published_results/stage07_awgn_dense_formal_results.csv`。
- S2 多径：Stage08 common-SNR `results/stage08_multipath_formal_common_snr_results.csv`。
- S2 帧内线性相位漂移：Stage10 `results/stage10_cfo_formal_result_summary.csv`。
- S2 遮挡：Stage12 `results/stage12_blockage_formal_result_summary.csv`。
- S2 突发/交织：Stage16 `results/stage16_burst_interleaving_comparison_raw_results.csv`。

每条数值结论必须同时记录方案、payload、信道、横轴定义、指标、SNR范围、CSV和图源。Stage17 未形成最终全信道 Gate，因此不从上述分散网格生成无约束全信道排名。
