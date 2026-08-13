阶段名称：S7_interleaving_burst_comparison
实验目的：研究固定 BCH 与卷积码方案在未知连续 BPSK 极性反转下的交织收益、位置敏感性、突发容限和工程代价。
主要输入：BCH 200/285 硬判查表链；CC 300/612 LLR+软 Viterbi 链；31 点 Es/N0、三比例、六位置。
完成内容：Stage00～16 已执行；Formal、全起点、时延、改善、推荐、51 图和最终集成均完成；历史 BCH/CC 无突发基线与 LDPC N640 无交织近码率 AWGN 基线均已审计接入，未重跑 Formal。
主要输出：S7_final_report.md、Formal/全起点结果、无突发与LDPC基线审计、编码参考汇总、四类清单、51图及统一SHA。
当前结论：BCH 推荐 ROW_COLUMN rows=15；CC 相对推荐 PSEUDORANDOM span=128，但 CC 未达到最小测试 2% 的最坏 FER 阈值。
已知问题：BCH多错误误纠、CPU平台依赖、CC/LDPC无统一复杂度操作量、擦除/强干扰扩展未做；LDPC只有AWGN数据，不能评价突发容限。
阶段状态：PASS
