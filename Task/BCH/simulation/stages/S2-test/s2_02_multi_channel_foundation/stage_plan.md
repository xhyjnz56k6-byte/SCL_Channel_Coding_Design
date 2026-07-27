# S2-02 Multi-Channel Foundation

实现固定单位能量多径、完整 N+3 线性卷积观测、确定性母噪声和已知信道线性
MMSE。正规方程使用半带宽 3 的 Cholesky；分解按 Case-SNR 点缓存，逐帧复杂度
为 O(N·bandwidth)，不做逐帧矩阵求逆。

Gate：`PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION`
