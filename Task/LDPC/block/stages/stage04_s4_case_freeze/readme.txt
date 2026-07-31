阶段名称：
stage04_s4_case_freeze

实验目的：
冻结 480、576 和不超过 640 比特目标对应的三个实际 Case。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/case_manifest.json
results/case_selection_report.md
results/frozen_cases.csv
results/target_actual_length_comparison.csv

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
