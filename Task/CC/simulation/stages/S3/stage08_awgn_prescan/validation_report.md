# Stage08 验证报告

Gate：`PASS_STAGE08_CC_AWGN_PRESCAN`

- 分支：`stage01-cc`
- baseCommit：`a80e3b96fcc4e68314a47070f5a4a7c08e43349c`
- originalContent：`6af44b8cee354cdbd49a2abc0ef5befed22995a4`
- validationRefresh：`e9e132f6de01ab512a2f310ad84b96f917b27dfe`
- mergeStatus：`NOT_MERGED`

已实际执行 Release 编译、预扫描 runner、逐点与绘图 checker、Stage07 回归和 `git diff --check`。六个 Case 均覆盖瀑布区，逐点 `SNR/actualRate/sigmaSquared` 公式、有限性、停止条件和 SNR 单调性检查通过；相同码率的 hard/soft 复用 payload、编码、母噪声和接收符号，soft FER 未劣于 hard。已生成 BER/FER 两张 PNG，PNG 签名、图数据和 SHA256 清单检查通过。

复验误码统计与原功能提交一致；计时字段受本机调度影响而刷新，故作为独立 `validationRefresh` functional range 保留。Stage09 正式区间已按 FER 约 0.005～0.8 冻结，步长均为 0.2 dB。

本 Stage 只用于定位 waterfall，不给出正式编码增益。远程验证延后至 Stage15 后统一 push；未合并 `main`。
