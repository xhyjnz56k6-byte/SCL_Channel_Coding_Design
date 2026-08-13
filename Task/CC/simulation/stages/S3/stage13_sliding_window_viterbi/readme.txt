阶段：Stage13 - 真滑窗 Viterbi 的 W/S/D 参数研究

目的：实现真正受窗口 W 限制的 survivor 存储，并在固定其余参数时分别研究窗口长度 W、滑动步长 S、回溯深度 D 对 BER/FER、内存、运算量和输出时延的影响。

作用：这是老师所要求“滑窗译码参数与时延统计”的核心实验。译码器不会保存全帧后再伪装成滑窗，而是使用 W x 64 survivor 单元并在在线输入时稳定输出。

得到的结果：无丢比特、无重复比特，算法单元和非法配置测试通过；正式 W/S/D 网格共 1,302 行，其中 CONTROL_W=372、CONTROL_S=372、CONTROL_D=558，Gate 为 PASS_STAGE13_FINAL_COMPARISON。

主要程序：src/true_sliding_window_viterbi.cpp 是最关键的滑窗实现；src/stage13_runner.cpp 运行正式实验；src/stage13_reference_runner.cpp 给出参考重放；scripts/process_stage13_full_wsd.py 生成完整 W/S/D 对比。

主要结果：results/stage13_full_wsd_formal_results.csv 是正式数据；stage13_final_ber_comparison.png、final_fer_comparison.png、final_latency_comparison.png、final_memory_comparison.png、final_complexity_comparison.png 为核心图；stage13_final_recommendations.csv 是参数推荐。

交付关系：这是最终上传的必选支撑结果，应与 Stage14 的时隙组织比较及 Stage15 的总表一起提供。
