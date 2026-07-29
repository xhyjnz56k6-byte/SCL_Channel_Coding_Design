# CC S3 最终修订汇总报告

任务边界：仅 300 bit 正式实验；不新增 200 bit 正式曲线。参数 K=7，生成多项式 171/133。SNR 横轴统一为 Es/N0 (dB)，sigmaSquared=1/(2*10^(snrDb/10))。当前模型是符号级离散 BPSK-AWGN，不是包含过采样、脉冲成形和接收滤波的完整波形仿真。

已完成：Stage10/11 补跑与图，Stage13 真滑窗修复与图，Stage14 四方案独立运行与图，Stage15 三张汇总图和两份详细 Markdown。

限制：当前仍是符号级离散 BPSK-AWGN，不是完整连续时间波形仿真；dense 层复用旧已验证 waterfall formal 数据，coarse 层为本轮新增全范围真实补跑。
