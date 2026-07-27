# Known Issues

- 高 SNR 零错误点是右删失/上界证据：有限帧数内未观测到错误，不等于真实 BER/FER 或 error floor 为 0。
- 对数图仅使用 `0.5/count` surrogate 显示零错误点；正式 CSV 的原始 `ber=0`、`fer=0` 未被改写。
- 高 SNR 多个零错误方案在当前 `50000` 帧上限下不能严格排序；结论改用 `3/N` 单侧 95% 上界和候选组表述。
- 时延统计受本机调度和缓存波动影响，适合同一批次内相对比较。
- `miscorrectionFrames` 与 `undetectedErrorFrames` 是当前接口下同一事件集合的语义别名。
- 本分支尚未合并 `main`，mergeStatus 保持 `NOT_MERGED`。
