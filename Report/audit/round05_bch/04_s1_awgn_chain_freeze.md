# S1 AWGN 主链路冻结

主循环由 `bch_awgn_simulation.cpp`/`bch_awgn_runner.cpp` 驱动，直接调用 Common 的 frame pool、BPSK、标准高斯噪声、AWGN、硬判决、指标、停止控制和 checkpoint 接口。

链路：公共 payload 帧池 → BCH 编码 → BPSK（0→+1，1→-1）→ 标准高斯母噪声 → AWGN → 零阈值硬判决 → BCH 译码 → payload 比较 → BER/FER 与 true/reported/miscorrection/failure → 时延/复杂度/内存 → 自适应停止 → summary。

内部输入是 payload `Eb/N0`；Common 方差为 `sigma²=1/(2*R*10^(Eb/N0/10))`。报告横轴只做 `Es/N0=Eb/N0+10log10(R)` 转换，不改变噪声或 BER/FER。

正式停止规则为最少 5000 帧、目标 200 个 payload 错帧、最多 50000 帧；不同点的处理帧数可以不同。FER 由恢复后的原始 payload 判定，不由译码器状态代替。
