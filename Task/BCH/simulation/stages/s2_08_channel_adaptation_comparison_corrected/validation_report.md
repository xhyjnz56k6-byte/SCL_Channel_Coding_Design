# Validation report

- Strict tolerance：1365 项；BRACKETED=805，EXACT=3，LOWER_BOUND_AT_TEST_LIMIT=174，BELOW_MINIMUM=367，NON_MONOTONIC=16。
- Burst theory：S200/S300 长度1、B200 1～6、B300 1～10、B300-426 1～14；全部合法起点共192点、960000帧，decodedFrameErrors=0。
- 分段边界 deterministic test：同一 BCH(15,11) 子块内2错失败；跨边界每块1错成功。
- Plot audit：22 张 PNG，全部有 figure-data CSV、源文件 hash、图注和独立标题。
- 旧 AWGN B300-426 约2 ms 值来自错误选择历史 formal timing；计时专用复测在 profile 预初始化和500帧 warm-up 后完成，只刷新时延，不替换 BER/FER。
- corrected channel comparison：PASS；CFO 数据仅来自 φ0=0。

Gate：`PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION_SCIENTIFIC_GATE`
