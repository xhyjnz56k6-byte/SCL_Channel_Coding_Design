# S2-01 Channel Contract

## 目标

冻结 BCH S2 第一批实验的五个 Case、固定多径、已知信道 MMSE、物理横轴、
指标、停止规则、绘图规范和后续边界。

## 非目标

不研究其他多径 profile、ZF、信道估计误差、频偏、遮挡、突发错误、交织、
卷积码、LDPC、软判决 BCH、自适应均衡、同步或导频。

## 范围

- 允许：`Task/BCH/simulation/current` 的多信道扩展、本 Stage 与 S2-02～04
  的脚本、测试、审计摘要和小型结果。
- 禁止：`Task/CC`、`Task/LDPC`、既有 BCH 数学核心、S1 正式 CSV、旧 Stage
  和旧实验结果。

## 五个 Case

| Case | payload | encoded | rate | 组织 | 译码器 |
|---|---:|---:|---:|---|---|
| BCH-S200 | 200 | 285 | 200/285 | 19×BCH(15,11,1)，filler=9 | SYNDROME_LOOKUP |
| BCH-B200 | 200 | 248 | 200/248 | BCH(255,207)，shortening=7，t=6 | BERLEKAMP_MASSEY_CHIEN |
| BCH-S300 | 300 | 420 | 300/420 | 28×BCH(15,11,1)，filler=8 | SYNDROME_LOOKUP |
| BCH-B300 | 300 | 390 | 300/390 | BCH(511,421)，shortening=121，t=10 | BERLEKAMP_MASSEY_CHIEN |
| BCH-B300-426 | 300 | 426 | 300/426 | BCH(511,385)，shortening=85，t=14 | BERLEKAMP_MASSEY_CHIEN |

## 信道与 MMSE

原始 taps 为 `[1, 0.65, 0.35]`，delays 为 `[0,1,3]`。先除以
`sqrt(1.545)` 做单位能量归一化。长度为 N 的发送块保留 N+3 个完整线性卷积
观测。接收端理想已知信道，使用

`(H^T H + sigma^2 I) x_hat = H^T y`

的带状 Cholesky 求解；每个 Case-SNR 点构造和分解一次，逐帧复用，不计算通用
矩阵逆。

## 横轴和指标

物理横轴为符号信噪比 `Es/N0 (dB)`：

`snrDb = sourcePayloadEbN0Db + 10*log10(frameRate)`。

FER 只比较最终恢复的 200 或 300 个 payload bit。BER、FER、真实/报告成功率、
误纠率、译码失败率、MMSE 前后硬判决 BER 和接收处理时间均由原始计数计算。
目标 FER 损失只允许在两条曲线都真实夹住目标时按 `log10(FER)` 线性插值；
禁止外推。AWGN FER 为零时 FER 放大倍数记为无效。

## 实验和绘图 Gate

- enhanced smoke 取代独立 prescan，并负责识别 waterfall 和冻结 formal 网格。
- formal：minFrames=5000，targetFrameErrors=200，maxFrames=50000。
- 图只用 matplotlib Agg 输出 PNG；不平滑、不拟合、不伪造零点。
- 每图必须有 figure-data CSV 和 `plot_manifest.json`，横轴换算可审计。
- S2-03 不重跑 AWGN，状态必须为
  `SKIPPED_BCH_S2_03_AWGN_RERUN` 和
  `REUSED_S1_FORMAL_AWGN_BASELINE`。
- 本批次止于 S2-04，不进入频偏、遮挡或突发错误。

Gate：`PASS_BCH_S2_01_CHANNEL_CONTRACT`
