# s2_06_short_blockage validation report

## 结果

1680 smoke 点、6300 参数 formal 点、156 SNR formal 点均通过。

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

`PASS_BCH_S2_06_SHORT_BLOCKAGE`

`mergeStatus = NOT_MERGED`
