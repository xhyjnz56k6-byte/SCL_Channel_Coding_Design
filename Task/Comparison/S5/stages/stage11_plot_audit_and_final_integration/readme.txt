阶段名称：Stage11 绘图审计与最终结果集成

任务目的：对 Stage10 正式数据进行可追溯绘图、汇总和方案推荐，形成最终报告可直接引用的图表与 CSV。
任务作用：将 744 个正式数据点转化为 BER/FER 曲线、时延与鲁棒性比较表、信道损失表和场景推荐表；不重新运行 Formal。
完成内容：以 Formal 合并 CSV（SHA-256：dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947）为唯一数据源；归档旧英文图；生成 86 张中文单指标折线图和 20 张 Aggregate 汇总图；禁止平滑、拟合、外推、柱图或以正数替换零误差点。
结果：中文重绘门禁 PASS_S5_STAGE11_CHINESE_REPLOT 与 Aggregate 图审计门禁 PASS_S5_AGGREGATE_PLOT_AUDIT 均通过。图和表位于 results/stage11/ 与 results/Aggregate/。
已知限制：CSV 中零误差点保留为 0，但不在对数坐标中绘制；只有相邻非零实测点夹住目标 FER 时才报告信道损失；不构造统一“鲁棒性总分”。
如何使用本目录：s5_scenario_recommendation.csv 用于方案结论；s5_channel_loss_table.csv、s5_latency_comparison.csv、s5_robustness_summary.csv 用于报告表格；plots/ 用于插图。
