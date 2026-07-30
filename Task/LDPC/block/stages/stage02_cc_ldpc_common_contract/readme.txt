阶段名称：
stage02_cc_ldpc_common_contract

实验目的：
冻结与 CC 一致的帧、Es/N0、噪声、统计和计时契约。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/cc_ldpc_contract_diff.md
results/common_contract.json
results/noise_policy_audit.md
results/result_schema.csv
results/snr_formula_audit.md
results/timing_contract.md

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
