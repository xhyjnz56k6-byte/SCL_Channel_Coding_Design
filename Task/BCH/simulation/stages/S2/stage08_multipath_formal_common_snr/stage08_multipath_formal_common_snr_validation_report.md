# Validation Report

- Results gate: PASS_STAGE08_COMMON_SNR_RESULTS_CHECK
- Plot gate: PASS_STAGE08_COMMON_SNR_PLOT_CHECK
- Final comparison gate: PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON
- Error-floor handling: PASS_ZERO_ERROR_CENSORING_WITH_3_OVER_N_UPPER_BOUND
- Point count: 296
- Total frames: 5599111
- TARGET_FRAME_ERRORS_REACHED points: 195
- MAX_FRAMES_REACHED points: 101
- Zero-error censored points: 56
- Solver residual max: 2.9431816804399681e-16
- NaN/Inf: 0
- Stage07 frozen model SHA-256: 2f7cb7895db229506d3fe809dc1f6d4bffc2b6f4be859695a76dca13f8ff62e6
- Legacy Stage08 result SHA-256: d7bbbda6c51fd13da3f76949cc8650fde7313f8e107ed1e734210185b2af4a14
- Legacy Stage08 grid SHA-256: 3ef3bf44ac1142ccb81db259bc72072d708965c8648fe645773755820d773e7b
- Legacy data label: LEGACY_WIDE_GRID_FORMAL

Error-floor note: zero-error rows keep raw `ber=0` and `fer=0` in the formal CSV, but reliability conclusions use `ZERO_OBSERVED_CENSORED` status and `3/N` one-sided 95% upper bounds.

`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。
