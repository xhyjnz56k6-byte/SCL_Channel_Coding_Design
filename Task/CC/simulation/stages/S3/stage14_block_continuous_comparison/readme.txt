阶段：Stage14 - 整块与真实在线连续时隙对比

目的：在真实逐 slot 到达和在线滑窗触发条件下，比较 300 bit 整块与 50x6、100x3、150x2 连续分块组织的 BER、FER、有效吞吐和首输出/平均/P95 决策时延。

作用：这是老师所要求“整块编码和按时隙比特长度分块”的直接对照实验。连续方案保持编码状态和打孔相位，收到每个时隙后更新缓存并触发真滑窗，最后统一终止。

得到的结果：Hard 与 Soft 各 372 行、合计 744 行正式数据，覆盖三种码率、四种组织和每 Case 31 个 SNR 点；26 张核心图和一致性检查通过，Gate 为 PASS_STAGE14_FINAL_DELIVERY。

主要程序：src/stage14_runner.cpp 执行在线时隙仿真；scripts/run_stage14.py 调度；scripts/process_stage14_revision.py 处理常规结果；scripts/process_final_delivery.py 生成最终交付图；check_stage14.py 做检查。

主要结果：results/stage14_online_slot_formal_results_all_decisions.csv 为总数据，hard.csv 和 soft.csv 可分别使用；stage14_*_ber_by_organization.png、*_fer_by_organization.png、*_goodput_by_rate_and_organization.png、*_first_output_latency.png、*_avg_p95_decision_latency.png 是主图。

交付关系：这是最终上传的必选支撑结果，直接证明时隙分块与整块的性能和时延差异。
