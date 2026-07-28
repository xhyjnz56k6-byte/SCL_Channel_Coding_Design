# Stage14 验证报告

Gate：`PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON`。base `07c6edabb333689fe341b109fb1e51e6606d9d65`；content `d1be888c0feca499b6a9c1c9a3d983dedbf6cb25`；未合并 main。

Release build、1000 个公平帧、8 方案行、全部长度/码率/分区/时延/吞吐/内存/操作数公式 checker、Stage13 审计回归及 `git diff --check` 实际通过。R12 滑窗与整块一致；R23 滑窗 BER/FER 0.00335/0.080，相对整块 0.00311/0.074 有已记录损失。连续方案首输出显著提前，推荐 100×3 作为折中。远程分支 `origin/stage01-cc` 已验证包含本 Stage 功能提交。
