# stage06_awgn_formal 已知问题

- 正式时延是当前 Windows/MinGW 单机实测值，会随机器负载变化；
- 高 SNR 零 BER/FER 点仅在对数图显示时使用 `0.5/denominator`，原始值保持 0；
- 当前分片 manifest 为每点一个本地 shard；stage05 已另行验证三分片逐计数等价；
- 逐点正式 CSV 与 checkpoint 保留在本地 `results/`，未提交 Git；
- 当前 AWGN 功能分支未 push；仅 stage01/02 独立基线分支已同步；
- 未合并 `main`，未创建或启动多径分支。
