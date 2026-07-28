# Stage08 AWGN 预扫描计划

先以 60 帧/点粗 smoke 自动定位每个码率 hard/soft FER≈0.5 中心，再按 0.5 dB 形成联合 prescan 区间。prescan 使用 minFrames=300、targetFrameErrors=30、maxFrames=2000，hard/soft 同码率共享 payload、编码、噪声和 receivedSymbols。

输出逐点 BER/FER、SNR/EbN0/sigma、实际码率、时延、吞吐、goodput、formal Case 建议范围、PNG/figure-data/manifest/checker。

Gate：`PASS_STAGE08_CC_AWGN_PRESCAN`
