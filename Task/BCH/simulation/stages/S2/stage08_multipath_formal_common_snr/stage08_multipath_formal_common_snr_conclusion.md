# stage08_multipath_formal_common_snr Conclusion

本结论只使用统一 `waveformSnrDb=0:0.5:18` 网格下的同 SNR 横向比较；旧 Stage08 标记为 `LEGACY_WIDE_GRID_FORMAL`，不作为最终横向排名依据。

Error-floor 处理规则：正式结果 CSV 中的 `ber=0` / `fer=0` 保持原始整数计数含义；在结论和高 SNR 排名中，零错误点标记为 `ZERO_OBSERVED_CENSORED`，只说明在当前帧数下未观测到错误，并使用单侧 95% 上界 `3/N` 给出可审查约束，不能当作真实 error floor 为 0。

`miscorrectionFrames` 与 `undetectedErrorFrames` 在当前译码接口语义下是同一事件集合的两个语义标签，不是互斥类别。

## 200 bit

- 低 SNR 观测 BER 最优：K200_M511K421；观测 FER 最优：K200_S15。
- 中 SNR 观测 BER 最优：K200_M511K385；观测 FER 最优：K200_M511K385。
- 高 SNR error-floor-aware BER 候选组：K200_M255K207;K200_M511K385;K200_M511K421，95% 上界约束 <= 3e-07。
- 高 SNR error-floor-aware FER 候选组：K200_M255K207;K200_M511K385;K200_M511K421，95% 上界约束 <= 6e-05。
- 码率优先：K200_M255K207；BCH 译码时延优先：K200_S15；MMSE 均衡时延优先：K200_S15。
- 不存在脱离 SNR 工作区间和有限样本 censoring 的单一绝对最优方案。

## 300 bit

- 低 SNR 观测 BER 最优：K300_M255K207；观测 FER 最优：K300_S15。
- 中 SNR 观测 BER 最优：K300_M511K385；观测 FER 最优：K300_M511K385。
- 高 SNR error-floor-aware BER 候选组：K300_M255K207;K300_M511K385;K300_M511K421，95% 上界约束 <= 2e-07。
- 高 SNR error-floor-aware FER 候选组：K300_M255K207;K300_M511K385;K300_M511K421，95% 上界约束 <= 6e-05。
- 码率优先：K300_M511K421；BCH 译码时延优先：K300_S15；MMSE 均衡时延优先：K300_M255K207。
- 不存在脱离 SNR 工作区间和有限样本 censoring 的单一绝对最优方案。

