# Validation report

- Build：PASS。
- `bch12_awgn_unit`、`bch_s2_mmse_unit`、`bch_s2_impairments_unit`：PASS。
- corrected 主扫角：180 点，全部 `initialPhaseDeg=0`，每点 5000 帧。
- corrected SNR 扫描：156 点，全部 `initialPhaseDeg=0`。
- 初始相位敏感性：40 点，φ0={0,45,90,135}°，rotation={0,30}°，未聚合。
- 理想补偿单元 Gate：实部样本差≤1e-12，hard-bit mismatch=0，payload mismatch=0。
- 原始结果位置：`Task/BCH/simulation/results/s2_batch2_corrected/s2_05/`。

Gate：`PASS_BCH_S2_CFO_PHI0_ZERO_CORRECTED`
