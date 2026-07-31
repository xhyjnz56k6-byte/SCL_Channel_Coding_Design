阶段名称：
stage08_direct_nms_integration

实验目的：
把 NMS 内核接入 Direct Tanner 图并完成独立验证。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/direct_nms_alpha_sanity.csv
results/direct_nms_dependency_scan.txt
results/direct_nms_noiseless.csv
results/direct_nms_reference_comparison.csv

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
