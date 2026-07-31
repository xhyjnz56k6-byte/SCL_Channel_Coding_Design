# S4-LDPC 正式最终报告

本实验使用 K=300、BG2、冻结 Direct 子矩阵、filler、Direct GF(2) 编码、BPSK、AWGN、LLR、Direct Layered SPA/BP 与 Direct Layered NMS。未使用 rateMatch、rateRecover、循环缓冲、HARQ、分块、交织、OMS 或 Flooding BP。

实际 Case 为 N480/N560/N640，码率分别为 0.625、0.5357142857142857、0.46875；正式 α 为 0.95/0.95/0.80。Es/N0 从 -5 至 10 dB、步长 0.5 dB。每点 BP/NMS 共享输入，双方均达到 200 错误且至少 1000 帧才停止，否则跑满 50000 帧。共处理 2019137 个配对帧，6 进程本次 wall time 为 191.955 秒。

结果包含 BER/FER 及置信区间、迭代、时延、操作分类、边消息更新、错误合法码字、BP/NMS 差异和三码长扩展比较。零错误点在原始 CSV 中严格保留 BER=0/FER=0；对数图只用不连线的空心向下标记表示 95% 上界，未以伪造小正数连接成平台。在当前最大 50000 帧/点的统计规模下，不对高 SNR error floor 作结论。

已知限制包括 Windows 调度导致的计时波动，以及有限帧下目标 FER 插值可计算范围。S5 可直接对接字段：actualLength、actualRate、algorithm、alpha、EsN0Db、BER、FER、迭代、时延、复杂度、seed、frame range、configHash。
