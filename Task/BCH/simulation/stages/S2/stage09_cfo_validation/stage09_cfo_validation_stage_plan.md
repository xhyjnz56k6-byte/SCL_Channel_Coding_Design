# stage09_cfo_validation 规格冻结

目标是验证整帧累计 30° CFO 的数学语义、复数 AWGN、实部硬判决、八 Case、MATLAB
索引以及 resume/shard 等价性。非目标是 CFO 估计、补偿、导频、相位跟踪和正式性能曲线。

相位律为 `phi[k]=k*pi/(6*(N-1))`，`k=0..N-1`。BPSK 符号能量为 1，实际码率为
`payloadLength/encodedLength`，`N0=1/(R*EbN0)`，复基带噪声的每个实维方差为
`N0/2=1/(2*R*EbN0)`。接收机仅以实部作零阈值硬判决，因此独立虚部噪声不影响当前判决；
0°时实部样本与 stage06 AWGN 完全退化一致。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 30°累计相位 | C++ runner | 4 点短向量、8 Case 首尾 | 非有限输入 | 首尾 0/π6 |
| 复数噪声 | C++/MATLAB | 固定 nI/nQ | NaN/Inf | 连续误差≤1e-12 |
| 硬判决与译码 | C++ runner | 0°、无噪声、8 Case | CLI 缺参 | mismatch=0 |
| 可恢复执行 | C++ runner | resume、3 shard | 非连续范围 | 整数统计一致 |

Gate：`PASS_STAGE09_CFO_VALIDATION`。
