阶段：Stage07 - 整块链路无噪声回归

目的：在进入 AWGN 性能仿真前，证明六个基础组合都能无误恢复 300 bit 电文。

作用：覆盖 R12/R23/R34 各自的 Hard 和 Soft，共六个 Case；检查编码长度、实际码率、终止状态、打孔观测数、非有限度量和 checkpoint 恢复。

得到的结果：六个 Case 各 100 帧均为 payloadBitMismatch=0、payloadFrameMismatch=0、nonFiniteMetricCount=0，最终状态均回到 0，Gate 为 PASS_STAGE07_CC_BLOCK_NOISELESS。

主要文件：scripts/run_stage07.py 是回归入口；results/stage07_block_noiseless_case_results.csv 是六 Case 结果；stage07_block_noiseless_checkpoint_roundtrip.csv 记录恢复测试。

交付关系：这是正式仿真的入场 Gate。它是必要验证，但不是老师要求的最终 BER/FER/时延结果。
