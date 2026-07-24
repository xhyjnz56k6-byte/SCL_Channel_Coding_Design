# BCH16W9 译码时延修复与 SNR 中文图

## 目标

1. 消除 BCH-B200、BCH-B300、BCH-B300-426 逐帧编码和译码路径中的
   `BlockBchProfile`/生成多项式重复构造。
2. 在同一构建、同一机器、同一测量协议下重新测量 BCH-S200、BCH-B200、
   BCH-S300、BCH-B300、BCH-B300-426 的平均软件译码时延。
3. 将 BER、FER、平均译码时延图的横轴由信息比特 `Eb/N0` 严格转换为
   BPSK 编码符号 `SNR=Es/N0`。
4. 生成标题、坐标轴和图例简短直观的中文 PNG 图及逐点 figure-data CSV。

## 非目标

- 不修改 BCH 编码参数、有限域算法、Berlekamp-Massey 或 Chien 搜索算法。
- 不改变已完成正式实验的 BER/FER 统计值。
- 不覆盖或删除任何旧 Stage、旧正式结果或旧图片。
- 不修改 Task/Common、Task/CC、Task/LDPC 或 MATLAB 官方验证结果。

## 功能范围

- `Task/BCH/simulation/current/src/bch_case_adapter.cpp`
- `Task/BCH/simulation/current/tests/`
- `Task/BCH/simulation/current/CMakeLists.txt`
- `Task/BCH/simulation/scripts/`
- `Task/BCH/simulation/stages/bch16w9_decode_timing_snr_figures/`

临时构建与逐帧实验输出只能放在 `Task/BCH/simulation/build/` 和
`Task/BCH/simulation/results/`，默认不提交 Git。

## SNR 定义与数据格式

当前信道为每个编码比特映射一个单位能量 BPSK 符号，因此：

```text
rate = payloadLength / encodedLength
snrDb = ebn0Db + 10*log10(rate)
```

横轴显示为 `SNR（dB）`，不得只改标签而保留原始 Eb/N0 横坐标。
figure-data CSV 同时保留 `sourceEbN0Db`、`frameRate` 和 `snrDb` 以便审计，
实际绘图只使用 `snrDb`。

## 时延测量协议

- 五种方案均使用同一 Release 构建。
- 每个正式 Eb/N0 点使用相同的公共帧池和冻结噪声策略重放。
- profile 和查找表必须在计时区间之外完成一次性初始化。
- 每个点先执行不计入统计的预热帧，再执行固定数量的计时帧。
- 译码计时区间只包围 `decodeBchFrame`，不包含编码、信道、文件 I/O、
  profile 构造、初始化和绘图。
- 重复运行并保留逐轮数据；发布值使用重复运行的中位数。

## 图面冻结

生成六张核心图：

| 分组 | 指标 | 中文标题 | 纵轴 |
|---|---|---|---|
| 200 比特 | BER | 200比特BCH误码率对比 | 误码率（BER） |
| 200 比特 | FER | 200比特BCH误帧率对比 | 误帧率（FER） |
| 200 比特 | 时延 | 200比特BCH平均译码时延 | 平均译码时延（μs） |
| 300 比特 | BER | 300比特BCH误码率对比 | 误码率（BER） |
| 300 比特 | FER | 300比特BCH误帧率对比 | 误帧率（FER） |
| 300 比特 | 时延 | 300比特BCH平均译码时延 | 平均译码时延（μs） |

图例仅使用：

- `分段 BCH(15,11)`
- `缩短 BCH(255,207)`
- `缩短 BCH(511,421)`
- `缩短 BCH(511,385)`

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| profile 一次构造并复用 | `bch_case_adapter.cpp` | 三种整块码重复编译码 | 静态检查逐帧路径 | 逐帧路径不再调用 `make*Profile()` |
| 修复不改变译码结果 | simulation tests | 五方案无噪声与可纠正错误 | 非法长度、超能力错误 | 原有测试和新增回归测试全 PASS |
| 时延重新测量 | timing runner/script | 五方案预热后重复测量 | 未预热/非有限值检查 | 数据完整，无 NaN/Inf，初始化不入计时 |
| SNR 严格转换 | plotting checker | 逐行公式复算 | 错误码率或假改标签 | 数值误差不超过 `1e-12 dB` |
| BER/FER 纵轴不变 | plotting checker | 对照 W8 正式摘要 | 丢点、重复点检查 | 逐点与来源 CSV 完全一致 |
| 中文图面 | plot manifest checker | 六张 PNG 与 figure-data | 禁止 Payload/Eb/N0/冗长图例 | 标题、轴名、图例全部符合冻结值 |
| 功能 Gate | CMake/CTest/checker | build、unit、integration、plot audit | mismatch/NaN/Inf 即停止 | `PASS_BCH16W9_FUNCTIONAL_GATE` |

## 阶段边界

阶段 B 完成功能实现、实验重跑和功能 Gate，不自动 commit 或 push。
阶段 C 只在用户另行要求后创建功能提交、审计文件、统一 Gate 和远程验证。
