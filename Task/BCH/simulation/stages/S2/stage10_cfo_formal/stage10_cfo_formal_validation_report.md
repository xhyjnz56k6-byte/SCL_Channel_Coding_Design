# stage10_cfo_formal 密集波形 SNR 验证报告

Gate：`PASS_STAGE10_CFO_FORMAL_DENSE_SNR_0_TO_8_STEP_0P5`

- 8 个 Case × 17 个 target waveform SNR，共 136 个正式点。
- target SNR 严格为 `0.0, 0.5, ..., 8.0 dB`；每个 Case 通过 `Eb/N0=targetSNR-10log10(actualRate)` 反算内部 Eb/N0。
- 停止规则：`minFrames=1000`、`targetFrameErrors=200`、`maxFrames=50000`。
- 63 点在 1000 帧达到目标错帧，24 点在 1000 帧以上达到目标错帧，49 点运行至 50000 帧上限；无点超限。
- 观测到 33 个零 BER、33 个零 FER；原始 CSV 保持零，log 图只对显示值使用 surrogate。
- 30° 线性跨编码帧相位模型、实部硬判决、无 CFO 补偿均保持不变。
- 8 张 PNG、8 份 figure-data、8 份 plot manifest 和 SHA-256 全部通过；无 PDF。
- MATLAB 抽查覆盖 4 Case × target SNR `0/4/8 dB`，共 12 样本；continuous error ≤ `1e-12`，hard/payload/status mismatch=0。
- Release 编译、CTest、checker 均 PASS。

DENSE_SNR_CODE_COMMIT：`3768c26a3f2cab3bc6b71a55b67cd985f1f6257e`。

当前分支：`stage10-12-bch-s2-dense-snr-rerun`；未合并 `main`。
