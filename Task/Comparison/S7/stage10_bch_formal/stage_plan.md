# Stage10 BCH Formal 计划

4 配置×31 Es/N0×3 ratio×6 position=2232 方案点、558 配对比较组。每组共享 payload/noise/burst/frame sequence；minFrames=1000、targetFrameErrors=200、maxFrames=50000、checkpoint=1000。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| syndrome table 复用 | BchCodecContext | 多帧无噪声/MATLAB | 每帧构造 | runner 单次初始化 |
| pair-stop | formal runner/checker | 同组 frames 一致 | 配置帧数不同 | 558 组一致 |
| checkpoint | binary+manifest | interrupt/resume 对照 | hash/case 不同 | 无重复/跳帧 |
| Formal CSV | checker | 2232 行 | NaN/Inf/count mismatch | 全部通过 |

