# Known Issues

- 零 BER/FER 点表示在有限帧数内未观测到错误，不等于真实错误率为零；对数图仅使用 0.5/count surrogate 显示。
- 时延统计受本机调度和缓存波动影响，适合作同一批次内相对比较。
- `miscorrectionFrames` 与 `undetectedErrorFrames` 是当前接口下同一事件集合的语义别名。
- 本分支尚未合并 `main`，mergeStatus 保持 `NOT_MERGED`。
