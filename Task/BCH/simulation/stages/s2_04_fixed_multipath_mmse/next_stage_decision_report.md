# 下一阶段决策报告

本报告只依据固定多径 + 已知信道 MMSE；未运行频偏、遮挡或突发错误。

1. 数值稳定性：未出现 NaN/Inf、Cholesky 失败或 MATLAB 硬判决 mismatch；
   MATLAB 最大均衡符号绝对差为 `8.216e-15`。
2. Waterfall：
- BCH-B200: FER≈0.1 位于 Es/N0=6.666 dB （观测 FER=0.1064）。
- BCH-B300: FER≈0.1 位于 Es/N0=6.461 dB （观测 FER=0.0922）。
- BCH-B300-426: FER≈0.1 位于 Es/N0=5.677 dB （观测 FER=0.105）。
- BCH-S200: FER≈0.1 位于 Es/N0=9.262 dB （观测 FER=0.1072）。
- BCH-S300: FER≈0.1 位于 Es/N0=9.939 dB （观测 FER=0.0978）。
3. 在 AWGN 与多径均夹住 FER=1e-3 的有效 Case 中，多径 SNR 损失最小：
   BCH-B300-426，
   `3.542 dB`。
4. 在同一有效集合中，FER=1e-3 时多径损失最大：BCH-S300，
   `7.393 dB`；FER 放大详见
   `fer_amplification_summary.csv`。
5. 分段码的误纠/译码失败明显高于整块强 BCH 的区域由
   `formal_summary.csv` 给出，不能用单一综合分数替代。
6. BCH-B300-426 的 t=14 在本固定多径下继续具有优势，目标 FER 损失和
   waterfall 均优于 BCH-B300 的相应对照。
7. MMSE 前后硬判决改善见 `mmse_hard_ber_summary.csv`，所有有效点均按原始
   BER 比值计算。
8. 接收代价：各 Case 加权平均均衡/译码/总接收时延见 `timing_summary.csv`；
   例如 BCH-B300-426 为
   `13.246/`
   `104.701/`
   `128.112 μs`。
9. 当前网格未观察到明确 error floor；这不构成对更低 FER 的外推结论。
10. 频偏实验建议优先取各 Case 的 FER≈0.1、0.01、0.001 插值 SNR，
    具体值见 `multipath_loss_summary.csv`。
11. 遮挡实验建议固定上述三个目标 FER 的多径 SNR，并由用户选择遮挡深度/时长。
12. burst+AWGN 建议以各 Case 多径 FER≈0.01 的 SNR 为背景点。
13. 进入 S2-05～07 前必须由用户确认：频偏范围/步长、遮挡深度/持续长度、
    burst 长度/位置/概率、是否维持相同 5000/200/50000 停止规则。

结论：等待用户选择下一阶段参数；不自动开始 S2-05、S2-06 或 S2-07。
