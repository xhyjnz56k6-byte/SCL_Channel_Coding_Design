阶段名称：
stage10_alpha_smoke_scan

实验目的：
定位各实际码长 waterfall 并执行 alpha 粗搜索。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/alpha_coarse_curve_summary.csv
results/alpha_coarse_point_results.csv
results/alpha_local_search_plan.csv
results/stage10_alpha_coarse_each_length.png
results/stage10_alpha_coarse_each_length_figure_data.csv
results/stage10_alpha_coarse_each_length_plot_check.md
results/stage10_alpha_coarse_each_length_plot_manifest.json
results/waterfall_estimate.csv

当前结论：
本阶段仅形成 smoke 级结论，不形成正式性能或编码增益结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
