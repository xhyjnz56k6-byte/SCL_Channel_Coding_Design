# CC S3 最终正式报告

## 最终结论

1. 在共同 Es/N0=2.0 dB 下，按本矩阵候选的最低 FER 排序为：
   R12=0, R23=0.006161, R34=0.07161。
   不同码率本身改变冗余度，因此这不是同吞吐条件比较。
2. Block Float Soft 在 FER=0.1 的插值 Es/N0 为：
   R12=-0.709 dB, R23=0.963 dB, R34=1.885 dB。
3. Block Soft 相对 Hard 的 FER=0.1 SNR 优势为：
   R12=2.085 dB, R23=1.927 dB, R34=1.857 dB。
4. 当前正式结果中 50x6、100x3、150x2 的 FER/BER 在每个 SNR 点完全重合；
   三者最终使用相同接收序列和滑窗边界，因此最终判决一致。组织方式仍改变真实
   slot 到达时刻，所以首次输出与 P95 时延并不重合。
5. Soft 首次输出最早的是 R23/50x6，
   223 symbols。
6. Soft P95 决策时延最低的是 R23/50x6，
   256 symbols。
7. 矩阵中总内存最小的 Soft 时隙代表是
   R12/50x6，
   26112 bytes。
8. 三种时隙的可靠性完全重合而时延不重合：编码器状态、打孔相位、滑窗边界和
   最终终止规则一致，保证最终判决一致；slot 到达粒度改变输出可用时刻。
9. W 决定窗口覆盖和缓存/首次输出，S 决定触发频率与输出节奏，D 决定回溯可靠性
   和回溯计算量。实际控制配置为 W 实验 S16/D70，S 实验 W160/D70，D 实验
   W160/S16。
10. Q8 相对 Float 在 FER=0.1 的 SNR 损失为：
    R12=0.006 dB, R23=0.008 dB, R34=-0.001 dB。
11. D112 的中位相对 FER 增幅为 0.005，D84 为 0.07；更深回溯保留
    更长路径历史，通常更可靠，但消耗更多存储和回溯操作。
12. 五类最终推荐如下：

- reliability_first: `R12_BLOCK_SOFT_FLOAT`，比较基准 `fixed_snr`；At Es/N0=2.0 dB, minimize measured FER.
- throughput_first: `R34_SLIDING_BALANCED`，比较基准 `fixed_snr`；At Es/N0=2.0 dB, maximize normalized goodput.
- latency_first: `R23_SLIDING_LATENCY_FIRST`，比较基准 `fixed_target_fer`；At interpolated FER=0.1, minimize first-output delay.
- memory_first: `R12_SLIDING_LATENCY_FIRST`，比较基准 `fixed_target_fer`；At interpolated FER=0.1, minimize total decoder memory.
- balanced: `R12_SLIDING_LATENCY_FIRST`，比较基准 `fixed_target_fer`；At interpolated FER=0.1, minimize a fixed weighted score of required SNR, first-output delay, memory and CPU time.

## 数据与限制

Stage14 统一表包含 Hard 372 行、Soft 372 行，共 744 行。Stage13 本轮没有补跑
D126；实际 W/S/D 控制变量与最初计划略有差异，但已有数据足以支持趋势结论，
不得声称测试了未运行参数。所有 FER=0.1 结论仅在真实点覆盖目标时使用相邻点的
对数域插值；共同工作点使用 Es/N0=2.0 dB。CPU 时间仅代表本机 Release 构建。
