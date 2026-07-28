# stage12_blockage_formal 密集波形 SNR 验证报告

Gate：`PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_B_DENSE_SNR_0_TO_8_STEP_0P5`

- 实验 A 保留原 64 个比例扫描点，实验 C 保留原固定绝对长度结果；未重跑、未改动其数值和图。
- 实验 B 重跑 8 个 Case × 17 个 target waveform SNR，共 136 点；A+B 正式点共 200 点。
- target SNR 严格为 `0.0, 0.5, ..., 8.0 dB`；内部 Eb/N0 按每个 Case 的 actualRate 反算。
- 遮挡模型保持 10%、零幅度、遮挡期间保留噪声、随机逐帧起点、非环绕、无交织。
- 停止规则：`minFrames=1000`、`targetFrameErrors=200`、`maxFrames=50000`；实验 B 136 点均在 1000 帧达到目标错帧。
- A 行与基线 92d3df7 中的原始 A 行逐字段一致；原始零值保持不变。
- 4 张新 SNR PNG、4 份 figure-data、对应 plot manifest 和 SHA-256 全部通过；比例图未重绘。
- MATLAB 抽查覆盖 4 Case × target SNR `0/4/8 dB`，共 12 样本；continuous error ≤ `1e-12`，hard/payload/status mismatch=0。
- Release 编译、CTest、dense SNR checker 均 PASS。

DENSE_SNR_CODE_COMMIT：`3768c26a3f2cab3bc6b71a55b67cd985f1f6257e`。

当前分支：`stage10-12-bch-s2-dense-snr-rerun`；未合并 `main`。
