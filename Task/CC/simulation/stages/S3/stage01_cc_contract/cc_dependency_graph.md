# CC S3 Stage 依赖图

```text
stage01_cc_contract
  -> stage02_trellis_encoder
     -> stage03_hard_viterbi
     -> stage04_soft_viterbi
        -> stage05_matlab_reference
           -> stage06_puncturing
              -> stage07_block_noiseless
                 -> stage08_awgn_prescan
                    -> stage09_awgn_formal
                    -> stage10_traceback_study
                    -> stage11_soft_quantization
              -> stage12_continuous_encoder
                 -> stage13_sliding_window_viterbi
                    -> stage14_block_continuous_comparison

stage01..stage14
  -> stage15_cc_s3_integration
```

Gate 规则：

- 任一前序 Gate 未 PASS，禁止开始依赖它的性能实验。
- smoke 未通过，禁止 prescan。
- prescan 未通过，禁止 formal。
- mismatch、NaN、Inf、长度错误或 checker 失败时停止当前 Stage。
- Stage15 必须重新执行总回归，不能只汇总历史 PASS 文本。
