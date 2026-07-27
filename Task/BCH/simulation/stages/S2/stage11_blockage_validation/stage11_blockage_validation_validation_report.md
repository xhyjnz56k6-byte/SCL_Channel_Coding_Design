# stage11_blockage_validation 验证报告

Gate：`PASS_STAGE11_BLOCKAGE_VALIDATION`

- Release 构建与 CTest 1/1 PASS；MATLAB 固定向量与 checker PASS。
- 遮挡在 BPSK 符号层实施；遮挡区信号幅度为 0，AWGN 保留。
- L=0 与 a=1 退化、首/中/末边界、L=1/L=N、越界和非法幅度拒绝通过。
- 8 Case 的比例换算、实际比例、逐帧随机起点范围通过。
- 连续执行、resume、三 shard 合并的整数统计及噪声校验和一致。
- MATLAB 连续值、mask 与 hard bit mismatch=0。
- 100000 个纯噪声遮挡样本的原始硬判决 BER 位于 [0.48,0.52]。
- stage12 锚点、比例表、代表比例和 SNR 网格已冻结并由后续 formal 使用。

功能范围：`3ec3e28cf6fe78f769a9878fe8683e634ed99217...10d85af8b99aeb44c118a312104348190c1bc997`。
