阶段名称：
stage01_legacy_code_audit

实验目的：
只读审计旧参考工程的 Stage19、Stage23g-Rerun 与 Stage15b。

主要输入：
payloadLength=300；BG2；Direct；BPSK-AWGN；Es/N0；BP/NMS；maxIterations=32。

完成内容：
已真实完成本阶段规定的代码、测试、smoke 或只读审计，并生成可复查结果。

主要输出：
results/legacy_code_inventory.csv
results/legacy_risk_report.md
results/legacy_source_map.csv
results/stage15b_nms_flow.md
results/stage19_parameter_flow.md
results/stage23g_direct_bp_flow.md

当前结论：
本阶段尚未形成正式性能结论。

已知问题：
正式 formal 尚未启动；smoke 零错误点只能解释为样本上界。

阶段状态：
PASS
