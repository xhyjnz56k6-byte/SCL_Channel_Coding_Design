# Stage14 无交织连续突发错误正式实验计划

## 目标

- 对 Stage13 冻结的 8 个 BCH Case 和突发长度集合执行无交织正式实验。
- 采用逐点独立停止、1000 帧 checkpoint、整数计数和可复算 BER/FER。
- 输出正式 CSV、MATLAB 抽查、13 张 PNG、逐图 figure-data、plot manifest 和 SHA-256。

## 非目标与边界

- 只使用 `interleaverMode=NONE`，AWGN 关闭，不实现 Stage15 交织比较。
- 不修改 Stage01～Stage13、稳定 BCH 核心、Case contract 或 `Task/Common`。
- 所有新增文件仅位于本 Stage 目录。

## 冻结接口

- 点集：8 Case × Stage13 `stage14BurstLengthsByPayload`。
- burst：`FLIP_CONTIGUOUS_BITS`、`RANDOM_PER_FRAME`、不回绕。
- 停止规则：`minFrames=1000`、`targetFrameErrors=200`、
  `maxFrames=50000`、`checkpointIntervalFrames=1000`。
- 停止只依据恢复 payload 的错误帧数。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 正式点与停止规则 | C++ runner/config | 128 个冻结点逐点运行 | 非法点、非法停止参数 | 点集完整且不超过 50000 帧 |
| 原始统计 | raw results/checker | 整数分子分母复算 | NaN/Inf、计数不守恒 | BER/FER/状态率全部一致 |
| checkpoint/shard | runner/checker | 每点 checkpoint、merge audit | SHA/commit/config 不一致 | 确定性统计一致 |
| MATLAB 抽查 | MATLAB/reference CSV | K200/K300 分块和整块三类点 | 位置、payload、status mismatch | mismatch 全为 0 |
| 绘图发布 | plot/checker | 13 张 PNG 与逐图数据 | 零值回写、非 PNG、缺 hash | 全部 plot manifest 通过 |

## Gate

`PASS_STAGE14_BURST_FORMAL`

