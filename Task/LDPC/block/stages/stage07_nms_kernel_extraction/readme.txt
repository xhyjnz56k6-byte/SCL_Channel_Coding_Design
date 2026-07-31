阶段名称：
stage07_nms_kernel_extraction

实验目的：
从标准链路中隔离 Layered NMS 校验节点更新内核。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/nms_dependency_scan.txt
results/nms_kernel_design.md
results/nms_kernel_unit_test.csv
results/nms_stage15b_regression.csv

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
