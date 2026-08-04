# S6 已知问题

- BCH-S200 与 BCH-B200 是不同码型、不同组织、不同码率、不同纠错能力的工程组合，BER/FER 差异不能全部归因于 lookup 与 BM。
- BCH 内存使用 `EXACT_FROM_TYPE_AND_COUNT`，不包含通用 STL 分配器隐藏元数据。
- CC 历史 Formal 非严格 pair-stop；Hard/Soft 与 Block/Slot 是两个独立维度。
- LDPC 主结果仅 maxIter=32；10/20/30 未完成正式性能对比。
- CPU 时延是平台相关观测值；BCH 本轮环境电源方案为“平衡”。
- 高 SNR 零 BER/FER 保留在数据中但不绘制；曲线终止不表示真实 error floor。
- 工作区按用户要求未 commit、未 push、未 merge。
