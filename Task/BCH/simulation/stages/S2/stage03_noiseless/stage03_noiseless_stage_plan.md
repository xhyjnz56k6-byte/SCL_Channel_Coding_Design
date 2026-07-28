# stage03_noiseless 规格冻结

8 个 Case 分别覆盖全 0、全 1、0101、1010、首位单 1、末位单 1、固定 seed
样本和 1000 个随机帧。链路固定为编码、BPSK、`y=x`、硬判决、译码和 payload
恢复。

每 Case 共 1007 帧，总计 8056 帧。分块 filler、多码块边界和缩短位恢复由对应
Case 的完整编码/恢复路径覆盖。

Gate：`PASS_STAGE03_NOISELESS`

BER、FER、payload mismatch、decoder failure、miscorrection 和 undetected error
必须全部为零；`trueSuccessFrames=totalFrames`；8 个 C++/MATLAB 样本编码和恢复
mismatch 必须为零。
