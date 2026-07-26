# 严格均匀随机起点算法

合法起点数为 `legalCount = N-L+1`。算法先从
`burstDomainValue(seed, frameIndex, retryDomain)` 获取确定性64位样本，再拒绝
区间 `[0, 2^64 mod legalCount)` 内的样本，最后执行 `% legalCount`。

因此所有合法余数拥有相同数量的64位原像，不存在直接取模造成的偏差。每次
重试由 `seed/frameIndex/domain/attempt` 唯一派生，不使用全局可变 RNG 状态，
不会破坏 checkpoint/resume 或 shard 一致性。

单元测试验证：

- 相同输入完全可复现；
- 所有结果位于合法范围；
- 不同 seed 改变序列；
- 固定大样本覆盖全部合法起点；
- 频数通过保守的卡方 sanity check。

统计 sanity check 仅用于发现明显实现错误，不作为均匀性的数学证明。
