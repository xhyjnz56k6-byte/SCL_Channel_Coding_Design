# S2-04 Fixed Multipath MMSE

执行两轮 enhanced smoke、自动冻结 formal 网格、正式多径实验、AWGN 对比、
固定输入独立参考、checkpoint/resume/shard 等价性、科研 PNG 与审计。

Formal 停止规则：minFrames=5000、targetFrameErrors=200、maxFrames=50000。
第一轮 smoke 为五 Case × 5 点 × 200 帧；加密 smoke 对分段 Case 使用
8–16 dB、对整块 Case 使用 5–11 dB，每点 500 帧。正式网格只能由 smoke
覆盖和目标 FER 夹取规则生成。

Gate：`PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE`
