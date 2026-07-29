# Stage09 规格冻结：整块卷积码 AWGN 正式实验

## 目标

对 Stage08 冻结的六个整块 Case 执行正式 AWGN 仿真，输出可审计的 BER、FER、时延、吞吐和有效吞吐结果，并验证 checkpoint/resume/shard/merge 的连续性和防覆盖语义。

## 非目标

- 不改变 Stage01～08 的编码、打孔、译码和随机策略。
- 不研究有限回溯、软量化、滑窗或分块流水线。
- 不对曲线范围外的编码增益进行外推。

## 允许范围

仅 `Task/CC/simulation/stages/S3/stage09_awgn_formal/`。

## 禁止范围

`Task/Common/`、`Task/BCH/`、`Task/LDPC/`、其他 CC Stage 和既有实验结果均不得修改。

## 冻结配置与数据语义

- payloadLength=300，zeroTailBits=6，masterSeed=2026072001。
- minFrames=5000，targetFrameErrors=200，maxFrames=50000。
- checkpointIntervalFrames=1000；R12 SNR step=0.2 dB，R23/R34 SNR step=0.1 dB。后两者的 Stage08 区间端点相差奇数个 0.1 dB，采用 0.1 dB 才能同时包含两端并形成 hard/soft 共用点。
- Case 范围逐项复制 Stage08 的 `stage08_awgn_prescan_formal_case_ranges.csv`。
- 同码率、同 SNR 的 hard/soft 从 frameIndex=0 开始，复用 payload、编码比特、标准高斯母噪声和 receivedSymbols。
- shard 按 `(rateId, snrDb)` 工作单元分配；每个单元内部 frameIndex 必须为 `[0, framesProcessed)` 连续区间。
- checkpoint 原子替换且绑定配置；resume 只接受匹配 checkpoint。
- 单元结果文件只允许首次创建；merge 拒绝重复、缺失、越界、跳帧和已存在的正式输出。
- 计时字段受运行环境影响；断点一致性以 payload/噪声索引、误码计数、停止原因和帧连续性字段为准。

## 接口与输出

- C++ runner：`stage09_awgn_formal_runner <runtimeDir> --shard-index I --shard-count N [--resume]`。
- Python 驱动负责编译、断点对照测试、分片运行、合并、结果检查和绘图。
- 正式输出文件名遵循用户任务清单；运行时 checkpoint/unit 文件位于忽略提交的 `runtime/`。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 六 Case 正式统计 | C++ runner + merge 脚本 | 77 个冻结点均达到合法停止条件 | 缺点/越界点被拒绝 | 全点公式和停止条件 PASS |
| hard/soft 公平性 | rate/SNR 工作单元 | 重叠点共享 frame/noise 序列 | frame 摘要不一致被拒绝 | 公平字段 PASS |
| checkpoint/resume | runner 二进制 checkpoint | 中断后恢复与连续运行确定性字段一致 | 配置不匹配 checkpoint 被拒绝 | resume 对照 PASS |
| shard/merge | unit 文件与 merge checker | 两分片覆盖全集 | 重复、缺失、跳帧、覆盖均被拒绝 | shard/merge PASS |
| 科研结果与图 | plot/check 脚本 | 五类 PNG、图数据、哈希、有限值 | 非法公式/PNG/外推被拒绝 | plot/check PASS |
| 审计边界 | manifest + CC audit | functional range 与 Git diff 一致 | 越界文件被拒绝 | 审计 PASS |

## Gate

`PASS_STAGE09_CC_AWGN_FORMAL`
