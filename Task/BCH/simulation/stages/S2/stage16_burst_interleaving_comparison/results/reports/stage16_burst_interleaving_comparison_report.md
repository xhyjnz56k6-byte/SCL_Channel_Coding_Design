# Stage16 AWGN+突发信道适应性及内部综合比较报告

- 正式网格：8 Case × 3 配置 × 37 SNR = 888 点
- SNR：0～18 dB，步长 0.5 dB；逐 Case 使用 actualRate 换算 Eb/N0
- 代表性突发长度：K=200 为 12 bit，K=300 为 8 bit
- 最佳方式分布：{'ROW_COLUMN': 7, 'PSEUDORANDOM': 1}
- 最佳深度分布：{'16': 6, '4': 2}
- 正式累计帧数：22013839
- 停止原因：{'TARGET_FRAME_ERRORS_REACHED': 467, 'MAX_FRAMES_REACHED': 421}
- MATLAB：固定向量 96/96，SNR 换算 888/888
- Gate：`PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_FUNCTIONAL`
- 组级 Gate：`PASS_BCH_S2_BURST_INTERLEAVING_STAGE13_TO_STAGE16_FUNCTIONAL`

## 数据驱动结论

1. 无交织抗突发能力、FER 增长速度和码块边界敏感性以 Stage14 tolerance/affected-block CSV 为准；分块方案在短突发处更快进入高 FER，不能外推为其他信道结论。
2. K300 双块方案的边界影响已保留在 Stage14/15 受影响码块统计中；本阶段不以单个起点替代随机起点总体统计。
3. Stage15 自动选择显示最佳必需交织器并非全部 Case 一致：{'ROW_COLUMN': 7, 'PSEUDORANDOM': 1}。
4. D=4/8/16 的选择并非预设；最佳深度分布为 {'16': 6, '4': 2}，收益是否饱和以 depth CSV 的原始点为准。
5. 分块与整块的交织收益只在本次冻结突发长度和停止规则内比较，不宣称跨信道优势。
6. 交织缓存为实际编码长度 bit，时延来自 Stage15 原始累计计时，未用估计值替代。
7. 可比较点的目标 FER SNR 恢复范围为 -0.043～0.016 dB。
8. K=200 与 K=300 使用不同代表突发长度，推荐配置按 Case 保存在 recommendation matrix。

本报告只形成连续突发与 AWGN+连续突发内部结论，不形成全部信道最终排名。
