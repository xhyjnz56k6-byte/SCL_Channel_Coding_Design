# S5 Stage10–11 Final Execution Report

## 1. Execution summary

All four required Gates passed. Stage10 executed the frozen 372 paired tasks / 744 scheme-points; Stage11 generated audited line plots and tables.

## 2. Pre-change Git state

- Root: `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design`
- Branch: `S5-Compare`
- HEAD/main/origin-main at audit: `ef56314e06cf2169744ee33b56ad2aea6d9815ca`
- Tracked diff was empty; untracked scope was `Task/Comparison/S5/` only.

## 3. Pre-Formal findings and fixes

Decoder construction polluted prior CC timing, timing fields were incomplete, checkpoint/resume was not Formal-grade, S4 regression was absent, and 10% blockage saturated CC. The archived pre-fix state is `archive/v01_20260802_before_formal_readiness_fixes/`.

## 4. Decode timing fairness

`CodecContext` caches CC trellis/encoder/Soft Viterbi and both LDPC graphs. Every point has 10 untimed warm-ups; decode timing is `steady_clock` LLR-to-payload/status and decoded results are consumed. Twelve before/after regression rows have exact integer reliability counts.

## 5. Checkpoint/resume

Four 3000-frame cases passed continuous versus 1000-frame interruption/resume exact reliability, iteration, stop, sequence and result hashes. Completed points return `SKIPPED_ALREADY_COMPLETE` after hash/config audit.

## 6. Complete timing metrics

Formal records impairment, AWGN, equalization, projection, LLR generation, channel processing, decode and total receiver algorithm timing with average/median/P95/max. P95 uses `ceil(0.95*N)-1`; CC iteration fields are NA.

## 7. S4 to S5 LDPC regression

21/22 raw points had overlapping Wilson intervals. The isolated N480 2.5 dB mismatch was exactly reproduced for the historical 1000 frames, then the frozen S4 stream was extended to 50000 frames (FER 0.81188), overlapping S5 FER 0.80806. Gate PASS.

## 8. 5% blockage supplemental Smoke

44/44 points completed and passed data/model/pair checks. Both CC curves remain near saturation, recorded as `KNOWN_CC_DYNAMIC_RANGE_FAILURE_NO_THIRD_TUNING` under the approved fallback.

## 9. 10% stress case

Historical 10% known blockage remains `KNOWN_BLOCKAGE_10_PERCENT_STRESS_CASE` only. It is not mixed into the 5% Formal dataset.

## 10–12. Formal scale and channel status

- Config hash: `41ee48b2e2a5d33e9e0177157ea6986c936a5abbe4d8ec54aa500c0aa05e528f`
- Paired tasks: 372
- Scheme-points: 744
- Paired frames: 8115263
- Scheme decodes: 16230526

- AWGN: 124 points, 3923376 scheme frames, PASS
- CFO_30_DEG: 124 points, 3721082 scheme frames, PASS
- FIXED_MULTIPATH_REAL_MMSE: 124 points, 2594954 scheme frames, PASS
- KNOWN_BLOCKAGE_5_PERCENT: 124 points, 2234516 scheme frames, PASS
- LINEAR_TIME_VARYING_FREQUENCY: 124 points, 3578686 scheme frames, PASS
- UNKNOWN_BURST_5_PERCENT_ISR_10DB: 124 points, 177912 scheme frames, PASS

## 13–14. Formal and plot Gates

- `PASS_S5_FORMAL`
- `PASS_S5_PLOT_AUDIT` (86 audited line figures)

## 15. BER/FER conclusions

Measured results are reported per channel and fairness group in the Formal CSV. Zero-error observations remain literal zero; no error floor is claimed. The 5% known erasure is especially unfavorable to the non-interleaved CC schemes, while LDPC—particularly N640—retains much stronger reliability in that controlled model.

## 16. Timing conclusion

The smallest mean measured decode latency entry is LDPC_BG2_N480_NMS under AWGN / RATE_NEAR_2_3 (113.377 us averaged over the SNR grid). These are current Windows Release software measurements, not hardware latency guarantees.

## 17. Robustness conclusion

All degradation metrics use each scheme's own AWGN baseline. Channel loss at FER 0.1/0.01 is reported only when adjacent real nonzero points bracket the target; no extrapolation and no unified score are used.

## 18. Scenario recommendations

- AWGN / RATE_NEAR_2_3: CC_R23_BLOCK_FLOAT
- AWGN / RATE_NEAR_1_2: LDPC_BG2_N640_NMS
- FIXED_MULTIPATH_REAL_MMSE / RATE_NEAR_2_3: CC_R23_BLOCK_FLOAT
- FIXED_MULTIPATH_REAL_MMSE / RATE_NEAR_1_2: LDPC_BG2_N640_NMS
- CFO_30_DEG / RATE_NEAR_2_3: CC_R23_BLOCK_FLOAT
- CFO_30_DEG / RATE_NEAR_1_2: LDPC_BG2_N640_NMS
- LINEAR_TIME_VARYING_FREQUENCY / RATE_NEAR_2_3: CC_R23_BLOCK_FLOAT
- LINEAR_TIME_VARYING_FREQUENCY / RATE_NEAR_1_2: LDPC_BG2_N640_NMS
- KNOWN_BLOCKAGE_5_PERCENT / RATE_NEAR_2_3: LDPC_BG2_N480_NMS
- KNOWN_BLOCKAGE_5_PERCENT / RATE_NEAR_1_2: LDPC_BG2_N640_NMS
- UNKNOWN_BURST_5_PERCENT_ISR_10DB / RATE_NEAR_2_3: CC_R23_BLOCK_FLOAT
- UNKNOWN_BURST_5_PERCENT_ISR_10DB / RATE_NEAR_1_2: LDPC_BG2_N640_NMS

## 19. Known issues

- Both CC curves remain saturated in the approved 5% contiguous-erasure model; no third fraction was tuned.
- CFO and linear time-varying frequency models have no compensation and are controlled comparison models.
- Multipath uses known real taps and a diagonal Gaussian LLR approximation.
- Burst mask is unknown to the receiver and nominal AWGN LLR is intentionally mismatched.
- Timing is host/software specific; maximum values include OS scheduling outliers.

## 20. Git status

No commit, push, or merge was performed. Stage manifests record `NOT_RUN_NO_COMMIT_AUTHORIZATION`; `main` was not merged.

## 21. Not executed

- No commit or push.
- No merge to `main`.
- No S6 or S7 work.
- No third blockage tuning and no real-satellite Doppler claim.

## 22. Final Gate

- `PASS_S5_FORMAL_READINESS`
- `PASS_S5_FORMAL`
- `PASS_S5_PLOT_AUDIT`
- `PASS_S5_FINAL_INTEGRATION`

PASS_S5_STAGE10_11_COMPLETE
