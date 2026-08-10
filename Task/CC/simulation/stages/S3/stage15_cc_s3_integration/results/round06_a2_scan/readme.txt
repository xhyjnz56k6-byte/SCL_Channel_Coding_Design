目录用途：Round06-A2 卷积码 S3 正式结果裁定与第5章证据冻结，只保存定向扫描形成的二次审计结论。

文件说明：
1. round06_a2_s3_evidence_freeze.md：完整中文证据冻结报告。
2. round06_a2_stage_authority_matrix.csv：Stage09～15 权威来源矩阵。
3. round06_a2_ch5_parameter_freeze.csv：第5章参数与关键数值口径。
4. round06_a2_ch5_figure_selection.csv：正文、附录和禁用图选择。
5. round06_a2_s3_recommendation_freeze.csv：Stage15 五类最终推荐。
6. round06_a2_downstream_mapping.csv：S5、S6、S7 实际采用的卷积码配置。

数据来源：当前 results 中的正式原始 CSV、生成这些 CSV 的 runner、manifest/config/run 记录、recommendation/selection CSV、final report 和 readme；发生冲突时严格按上述顺序裁定。未读取 build、runtime、checkpoint、分片 unit CSV 或 archive 作为结论来源。

可修改性：本目录是可修订的扫描结论，但不得用它反向覆盖或修改既有正式 CSV、PNG、runner 和历史结果。后续发现新权威证据时，应保留本版并新增修订记录。

第5章使用方式：先引用参数冻结表与权威矩阵确定口径，再从图选择表选择 figure_data；当前正式 PNG 均为英文科研图，正文中文版本应在后续 Round06-B/C 基于既有 figure_data 重绘，不需要重跑仿真。

本轮结论：NO_RERUN_REQUIRED。
