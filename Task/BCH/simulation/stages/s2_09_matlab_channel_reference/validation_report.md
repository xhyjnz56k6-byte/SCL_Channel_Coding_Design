# s2_09_matlab_channel_reference validation report

## 结果

MATLAB 独立复算 4500 帧，样本误差不超过 1e-12，离散 mismatch 为 0。

## 实际执行

- Release 配置与编译：PASS
- Common CTest：7/7 PASS
- BCH simulation CTest（含 segmented、block、B300-426、AWGN、S2 多径、新信道）：9/9 PASS
- `check_bch_s2_batch2.py`：PASS
- resume/shard 正向与负向审计：PASS
- MATLAB 独立参考：PASS
- PNG/figure-data/hash/SNR/样式审计：PASS
- 远程功能提交验证：origin/bch-s2-batch2-cfo-blockage-burst-final-audit 包含本 Stage 所有 functional content commit

## Gate

`PASS_BCH_S2_09_MATLAB_CHANNEL_REFERENCE`

`mergeStatus = NOT_MERGED`
