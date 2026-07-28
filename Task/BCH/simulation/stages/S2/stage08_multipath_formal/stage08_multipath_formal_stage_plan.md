# stage08_multipath_formal 规格冻结

## 目标

在 stage07 冻结的同一固定多径、单位能量归一化、完整线性卷积、完美信道知识
和块线性 MMSE 下，按 24 点人工冻结 Eb/N0 网格正式运行 stage02 的 8 个 Case，
分别形成 200 bit 与 300 bit 的 BER、FER、译码/均衡时延和推荐结论。

## 非目标

不比较多径相对 AWGN 的损失；不动态搜索瀑布区；不改变网格、信道或均衡器；
不平滑、拟合、插值、删除或修正观测点。

## 停止、随机与分片

- `minFrames=5000`、`targetFrameErrors=200`、`maxFrames=50000`。
- stopReason 仅允许 `TARGET_FRAME_ERRORS_REACHED` 或 `MAX_FRAMES_REACHED`。
- `masterSeed=8080808`；frame identity 绑定 Case、channel、parameter、Eb/N0
  index、frame index 与 PAYLOAD/AWGN 域。
- 2 个 shard 按冻结 grid 行互斥分配，每个 point 的 frameIndex 从 0 开始，
  不同 shard 不包含相同 Case/Eb/N0 点。
- 每 1000 帧保存完整点内 checkpoint（整数计数、累计时间、时延样本与 residual）；
  重启从相同逻辑 frameIndex 继续。每完成一点刷新 shard CSV 并删除对应中间
  checkpoint；已完成点在重启时跳过。

## 提交资产

提交源码、配置、冻结网格、正式小型汇总 CSV、8 个 PNG、figure-data、
plot manifest、日志、checker、SHA-256、patch 和审计报告。`build/` 与
checkpoint 中间文件不提交。

## Gate

结果 checker、shard merge audit、checkpoint/resume、plot checker、SHA-256、
200/300 bit 结论和 Git 审计全部通过后，输出
`PASS_STAGE08_MULTIPATH_FORMAL`。
