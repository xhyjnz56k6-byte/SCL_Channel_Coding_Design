阶段名称：
stage13r_direct_bp_nms_smoke_rerun

实验目的：
用新冻结 α 在独立帧区复跑 BP/NMS smoke，并保留 MS 控制组核验旧现象。

主要输入：
K=300，实际码长 N480/N560/N640，Direct BG2 QC-LDPC，AWGN，最大迭代 32。

完成内容：
使用同源 payload、噪声和 LLR 完成真实译码、统计、检查与绘图。

主要输出：
带 95% CI 的逐点结果、四分类/agreement 指标、5 张主图与最终结论。

当前结论：
详见 results 下的最终报告。

已知问题：
本阶段是审计或 smoke，不是 formal；有限帧统计仍有置信区间限制。

阶段状态：
PASS
