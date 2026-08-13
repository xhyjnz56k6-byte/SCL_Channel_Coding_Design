阶段：Stage11 - 软判决量化研究

目的：评估 Float 与 Q3 至 Q8 量化软信息对 BER/FER、SNR 损失、时延和存储的影响，给出可实现的软判决位宽。

作用：将“理论软判决性能”落到硬件/实时实现可采用的量化配置上，并补充最终方案中的工程推荐。

得到的结果：三种码率、Q3-Q8 与 Float 的 prescan、粗网格和密集点均完成，共 931 行；均衡工程候选为 Q8，Gate 为 PASS_STAGE11_REVISION。

主要程序：src/stage11_soft_quantization_runner.cpp 是核心仿真；scripts/run_stage11.py 执行；check_stage11.py 检查；process_stage11_revision.py 后处理。

主要结果：results/stage11_soft_quantization_results.csv 为正式数据；stage11_quantization_snr_loss.png、latency.png、memory.png 反映损失与资源；stage11_quantization_recommendation.csv 记录推荐。

交付关系：仅在报告需要说明“软判决可采用何种量化”时上传。主交付中可选用 Stage15 的 stage15_quantization_snr_loss.png 代替本阶段原图。
