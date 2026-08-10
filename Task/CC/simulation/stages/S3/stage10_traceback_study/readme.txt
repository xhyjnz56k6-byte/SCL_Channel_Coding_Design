阶段：Stage10 - 有限回溯深度研究

目的：比较完整回溯与有限回溯深度 Dtb=35/49/70/84/98/112 的可靠性、存储量、运算量和译码时延，回答“回溯深度如何选”。

作用：把软/硬性能以外的工程代价显式量化，为滑窗译码参数和最终工程建议提供依据。

得到的结果：三码率、三个 FER 水平、六个有限深度及完整回溯均完成，正式 63 行结果；D84 的真滑窗复验通过，Gate 为 PASS_STAGE10_REVISION。

主要程序：src/stage10_traceback_study_runner.cpp 是核心仿真；scripts/run_stage10.py 执行；check_stage10.py 检查；process_stage10_revision.py 生成图表。

主要结果：results/stage10_traceback_study_results.csv 为正式数据；stage10_traceback_memory.png、cpu_latency.png、relative_fer_loss.png 和 memory_reliability_tradeoff.png 展示取舍；stage10_traceback_recommendation.csv 给出推荐。

交付关系：老师若要求解释滑窗“回溯深度/时延”，上传推荐表和一张内存-可靠性权衡图；它不是三种码率 BER/FER 主图的替代品。
