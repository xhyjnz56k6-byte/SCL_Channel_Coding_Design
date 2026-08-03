阶段名称：Stage11 plot audit and final integration
实验目的：Audit Formal data, generate traceable scientific line plots/tables, and integrate conclusions.
主要输入：PASS_S5_FORMAL and the exact merged Formal CSV.
信道数学模型：All comparisons remain relative to each scheme's own AWGN baseline; target-FER interpolation uses adjacent nonzero measured points only.
冻结参数：Source Formal SHA-256 dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947; no smoothing, fitting, extrapolation, bars, or zero replacement.
完成内容：原86张英文图已版本化归档；使用同一Formal CSV生成86张中文图和20张Aggregate图，并按目标FER覆盖优先级更新推荐表。
验证结果：PASS_S5_STAGE11_CHINESE_REPLOT；PASS_S5_AGGREGATE_PLOT_AUDIT。
主要输出：Plot tree, plot audit summary, scenario recommendation, channel loss, latency comparison, robustness summary.
当前结论：未重跑Formal，Formal CSV哈希未改变；中文图和Aggregate均可追溯到同一Formal CSV。
已知问题：Zero-error points are retained as 0 in CSV and omitted on log axes. Target FER loss is unavailable where adjacent nonzero measured points do not bracket the target. No unified robustness score is produced.
阶段状态：PASS
