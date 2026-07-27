# stage11_blockage_validation 规格与 Gate

符号层模型为 `y[k]=a[k]x[k]+n[k]`；矩形连续遮挡内 `a=0`，仍保留 AWGN。随机起点逐帧
均匀取自 `[0,N-L]`，使用独立 BLOCKAGE_START 域，不回绕、不交织。

| 需求 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|
| 模型退化 | L=0、a=1、noise=0/非0 | 越界/非法幅度 | 与 AWGN/固定向量一致 |
| 比例换算 | 8 Case 10% | rho 越界 | L=round(rho*N) |
| 随机起点 | resume、shard | 固定所有帧 | 身份可复现 |
| MATLAB | 8 点连续量/mask/bit | 索引边界 | mismatch=0 |
| 统计性质 | 100000 遮挡样本 | 偏离容差 | BER∈[.48,.52] |

Gate：`PASS_STAGE11_BLOCKAGE_VALIDATION`。
