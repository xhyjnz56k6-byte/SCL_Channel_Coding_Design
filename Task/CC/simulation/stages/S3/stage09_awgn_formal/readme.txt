阶段：Stage09 - 整块编码 AWGN 正式基线

目的：给出 300 bit 整块零尾卷积编码在 AWGN/BPSK 下，R12/R23/R34 与 Hard/Soft Viterbi 的正式 BER、FER、吞吐和译码时延基线。

作用：这是 S3 的“整块编码”对照组。它为后续有限回溯、量化、滑窗和连续时隙组织提供同一物理信道和编码参数下的参考数据。

得到的结果：正式结果由 186 行粗网格和 126 行密集点组成，共 282 行、5,295,134 帧；两层数据合并、公式、覆盖和绘图检查通过，Gate 为 PASS_STAGE09_TWO_LEVEL_REVISION。

主要程序：src/stage09_awgn_formal_runner.cpp 执行仿真；scripts/run_stage09.py 调度；scripts/merge_and_plot_stage09.py 合并并绘图；scripts/process_stage09_revision.py 做结果修订处理。

主要结果：results/stage09_two_level_merged_point_results.csv 是正式原始点；stage09_two_level_ber.png、fer.png、goodput.png、delay.png 和 hard_soft_fer.png 是可读图；results_analysis.md 与 stage09_two_level_report.md 给出解释。

交付关系：可作为整块性能附录上传；最终展示优先采用 Stage15 重新汇总的核心图和最终矩阵。
