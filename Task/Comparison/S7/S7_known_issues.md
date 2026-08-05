# S7 最终已知问题

- 分支名 `S7-Comparision` 是用户指定例外。
- BCH(15,11,1) 多错误模式可误纠；Formal 已记录 5,439,787 个未检出错误帧和 23,251,548 个误纠块。
- CC 所有配置在 10 dB 最坏位置下均未达到 FER≤0.1 的最小测试 2% 突发容限。
- 目标 FER=0.5 的 NONE 基线未被唯一包围，因此不报告 Es/N0 gain。
- Stage12 每起点 200 帧，FER 分辨率为 0.005。
- CPU 时间依赖本机；结构等待量不是物理时间。
- 已知连续擦除和未知连续强干扰扩展未做。
- S6 LDPC N560 仅为 AWGN-only 不兼容独立参考。
- Stage15 v01 图资产未通过 anomaly-scope Gate，已归档且禁止用于正式结论。
- 所有 S7 文件尚未 commit；未 push、未远程验证、未合并 main，functionalRanges 为空。
