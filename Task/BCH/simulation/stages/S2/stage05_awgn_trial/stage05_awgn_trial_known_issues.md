# stage05_awgn_trial 已知问题

- 本 Stage 是固定 500 帧基础设施试运行，不作为正式 BER/FER 性能结论；
- 高 SNR 零错误点在对数图上使用 `0.5/denominator` 作为显示替代值，原始数据仍为 0；
- 译码时延受本机负载影响，stage05 只用于 stage06 运行时估算；
- 生成的逐帧/明细结果保留于本地 `results/`，不提交 Git；
- 当前 AWGN 功能分支未 push；仅 stage01/02 基线已按用户指定单独同步；
- 未合并 `main`，未启动多径实验。
