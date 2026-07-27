# Stage13 突发错误与交织基础验证计划

## 目标

- 在不修改既有 BCH 编译码核心、Case contract 和公共随机数核心的前提下，实现连续 bit 翻转信道。
- 实现 `NONE`、`BLOCK`、`ROW_COLUMN`、`PSEUDORANDOM` 四种单帧双射交织。
- 验证 8 个 BCH S2 Case、逆置换、随机身份、checkpoint/resume、shard/merge 和 MATLAB 独立参考。
- 用 200 帧/点预扫冻结 Stage14、Stage15 的突发长度集合。

## 非目标

- 不实现多径、MMSE、CFO、短时遮挡或其他编码类型。
- 不修改 Stage01～Stage12、`Task/Common` 或稳定 BCH 编译码器。
- 不把交织用于普通 AWGN-only 场景。
- 不将可选卷积式交织纳入正式 Gate。

## 范围

允许范围仅为：

`Task/BCH/simulation/stages/S2/stage13_burst_interleaving_validation/`

Stage13 可以只读链接 Stage01、Stage02、BCH segmented/block 既有代码。

## 接口与数据格式

- burst：在合法区间 `start <= k < start + length` 对传输 bit 执行 XOR 1，不回绕。
- permutation：`output[k] = input[permutation[k]]`，逆操作满足
  `recovered[permutation[k]] = output[k]`。
- burst 随机身份包含 master seed、共享 stage identity、case、参数组、SNR 索引、
  burst-length 索引和 frame index；不包含交织模式。
- PSEUDORANDOM 置换由 Case、编码长度、深度和 interleaver seed 冻结，每帧不重新生成。
- 预扫固定为每点 200 帧；正式停止参数由后续 Stage 使用：
  `minFrames=1000`、`targetFrameErrors=200`、`maxFrames=50000`、
  `checkpointIntervalFrames=1000`。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 连续 bit burst | `cpp/stage13_*_core.*` | L=0/1/N、首尾、边界与跨块 | L>N、start 越界、回绕请求 | 翻转位置精确且长度不变 |
| 四种交织 | core 与 unit test | 双射、逆映射、D=4/8/16、不满矩阵 | 非法 mode/D、重复/遗漏/越界索引 | 四模式合法且 BLOCK≠ROW_COLUMN |
| PSEUDORANDOM 审计 | runner/permutation CSV | 重复生成 SHA 一致 | seed 缺失、文件/SHA 损坏 | C++/MATLAB 读取同一 canonical 置换 |
| 8 Case 全链路 | validation runner | 固定 payload、编码、交织、burst、解交织、译码 | 长度与 Case contract 不一致 | C++/MATLAB mismatch 全为 0 |
| 可复现性 | runner/checker | 连续、resume、shard/merge、乱序、重复 | 配置/随机身份改变 | 所有整数统计完全一致 |
| 参数预扫 | runner/checker | 8 Case、冻结 L、D 和四模式 | 缺点、NaN/Inf、非冻结参数 | 生成 Stage14/15 frozen parameters |

## Gate

只有构建、CTest、负向测试、MATLAB 对照、预扫、checkpoint/resume、
shard/merge、结果 checker 和审计 checker 全部通过时，输出：

`PASS_STAGE13_BURST_INTERLEAVING_VALIDATION`

Gate 失败时不得进入 Stage14。

