# Validation report

- C++ corrected vector export：3500 行，PASS。
- MATLAB 独立对照：35 组、3500 帧，PASS。
- received complex、perfect compensated 与 paired-AWGN 实部最大差均≤1e-12。
- hard bit、decoded payload、frame error mismatch 均为0。
- 结果同时保存于 corrected Stage 与 `results/s2_batch2_corrected/published/s2_09/`。

Gate：`PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE`
