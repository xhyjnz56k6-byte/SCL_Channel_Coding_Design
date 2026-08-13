阶段：Stage15 - CC S3 最终集成与交付

目的：只读取已通过 Gate 的正式数据，形成教师可直接审阅的 S3 总报告、方案矩阵、工作点和核心图，避免把预扫描或中间分片混入结论。

作用：整合 Stage09 的整块基线、Stage10 的回溯研究、Stage11 的量化、Stage13 的真滑窗参数研究和 Stage14 的在线时隙比较，覆盖老师要求的三种码率、BER、FER、有效吞吐和滑窗译码时延。

得到的结果：最终方案矩阵共 3,447 行，其中 Stage14 Hard 372 行、Soft 372 行；生成 12 张核心图和五类推荐，Gate 为 PASS_CC_S3_FINAL_DELIVERY。

主要程序：scripts/process_final_delivery.py 是最主要的总表和绘图程序；scripts/run_stage15.py 是入口；scripts/check_stage15_revision.py 检查数据来源和完整性；scripts/package_local_results.py 用于整理本地结果包。

必须优先查看的结果：results/cc_s3_final_formal_report.md、stage15_final_scheme_matrix.csv、stage15_final_recommendations.csv、stage15_fair_operating_points.csv。核心 PNG 为 block_soft_ber_by_rate、block_soft_fer_by_rate、slot_soft_fer、slot_soft_goodput、slot_first_output_latency、slot_avg_p95_latency、sliding_parameter_summary 和 latency_reliability_pareto。

交付关系：本目录是 S3 对外提交的首选目录；老师未特别指定时，优先上传本目录的报告、矩阵、推荐表和核心图，再按需要补充 Stage13/Stage14 的原始正式 CSV。
