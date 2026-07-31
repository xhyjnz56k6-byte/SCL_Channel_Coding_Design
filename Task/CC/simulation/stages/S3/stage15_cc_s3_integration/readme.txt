Stage15：CC S3 最终集成

运行 scripts/process_final_delivery.py 复用 Stage09/10/11/13 和 Stage14 正式 CSV，
生成最终矩阵、12 张核心图、公平工作点与五类推荐。运行
scripts/check_stage15_revision.py 做实质数据检查。

最终报告：results/cc_s3_final_formal_report.md
最终矩阵：results/stage15_final_scheme_matrix.csv
推荐表：results/stage15_final_recommendations.csv
公平工作点：results/stage15_fair_operating_points.csv
