# S2-03 AWGN Baseline Reuse

本 Stage 不重跑 AWGN。只审计 S1 五 Case 正式摘要及 BCH16W9 修复后时延来源，
记录 SHA-256、Git 来源、schema、范围、帧数和列映射，并逐点转换物理横轴：

`snrDb = sourcePayloadEbN0Db + 10*log10(frameRate)`。

状态：`SKIPPED_BCH_S2_03_AWGN_RERUN`；
`REUSED_S1_FORMAL_AWGN_BASELINE`。
