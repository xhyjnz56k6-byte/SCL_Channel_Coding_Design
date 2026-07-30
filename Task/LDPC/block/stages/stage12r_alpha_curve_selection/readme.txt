阶段名称：
stage12r_alpha_curve_selection

实验目的：
用 FER、平均译码时延和每帧 edge-message updates 三类曲线重新冻结各码长 α。

主要输入：
K=300，实际码长 N480/N560/N640，Direct BG2 QC-LDPC，AWGN，最大迭代 32。

完成内容：
使用同源 payload、噪声和 LLR 完成真实译码、统计、检查与绘图。

主要输出：
每码长 3 张全候选曲线、逐点结果、决策表、报告和 frozen_alpha_rerun.json。

当前结论：
详见 results 下的最终报告。

已知问题：
本阶段是审计或 smoke，不是 formal；有限帧统计仍有置信区间限制。

阶段状态：
PASS
