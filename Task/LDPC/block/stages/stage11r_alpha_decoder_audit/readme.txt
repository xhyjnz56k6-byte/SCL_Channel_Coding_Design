阶段名称：
stage11r_alpha_decoder_audit

实验目的：
审计 α=1.00 的 MS 语义、early-stop、错误合法码字、逐帧一致性和汇总隔离。

主要输入：
K=300，实际码长 N480/N560/N640，Direct BG2 QC-LDPC，AWGN，最大迭代 32。

完成内容：
使用同源 payload、噪声和 LLR 完成真实译码、统计、检查与绘图。

主要输出：
四分类、early-stop/fixed 对比、逐帧 agreement、代表帧 trace 与专项报告。

当前结论：
详见 results 下的最终报告。

已知问题：
本阶段是审计或 smoke，不是 formal；有限帧统计仍有置信区间限制。

阶段状态：
PASS
