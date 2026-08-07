# 权威结果源

优先级采用“人工确认正式目录 > 目录内CSV与配置 > 对应源码 > Round05-A > 历史冻结”。

- S1唯一最高权威：`Task/BCH/simulation/stages/S1/stage07_awgn_dense_formal`。
- S2直接正式目录：`stage08_multipath_formal_common_snr`、`stage10_cfo_formal`、`stage12_blockage_formal`、`stage14_burst_formal`；AWGN复用S1目录。
- `stage15_interleaving_formal`和`stage16_burst_interleaving_comparison`只作为第9章接口证据，本章不展开。
- 未使用旧Stage17/integration或`Report/data/frozen`覆盖人工正式目录。

Round05-A曾把S1压缩为五个核心codec方案并引用历史来源；人工目录实际含八个正式实验case，包括200 bit的两个额外511母码方案和300 bit双块BCH(255,207)方案。本章已按八个case纠正，旧审计文件保留不覆盖。
