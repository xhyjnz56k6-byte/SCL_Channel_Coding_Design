阶段名称：
stage11_alpha_local_refinement

实验目的：
执行局部 alpha 补点并分别冻结每个实际码长的 alpha。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/alpha_all_candidates.csv
results/alpha_selection_by_length.csv
results/alpha_selection_report.md
results/frozen_alpha.json
results/stage11_alpha_selection_each_length.png
results/stage11_alpha_selection_each_length_figure_data.csv
results/stage11_alpha_selection_each_length_plot_check.md
results/stage11_alpha_selection_each_length_plot_manifest.json

当前结论：
本阶段仅形成 smoke 级结论，不形成正式性能或编码增益结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
