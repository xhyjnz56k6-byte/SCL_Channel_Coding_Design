阶段名称：
stage05_direct_encoder_matrix

实验目的：
验证 Direct H/Hu/Hp 构造、GF(2) 编码和 payload/filler 映射。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/encoder_selfcheck.csv
results/matrix_summary.csv
results/payload_filler_mapping.csv
results/reference_comparison.csv
results/syndrome_selfcheck.csv

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
