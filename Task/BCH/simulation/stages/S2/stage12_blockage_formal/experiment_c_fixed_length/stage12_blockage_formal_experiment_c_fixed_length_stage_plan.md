# stage12 固定绝对遮挡长度实验 C

## 目标

在 stage12 已冻结的遮挡模型下，以固定绝对遮挡长度 `5、10、20、30` 个调制符号完成正式实验。
K200 使用 `Eb/N0=7.5 dB`，K300 使用 `Eb/N0=8.0 dB`，覆盖 8 个 BCH 案例，共 32 个点。

## 非目标

- 不修改 stage12 实验 A/B 的配置、结果或图。
- 不改变 BCH 编译码器、遮挡模型、随机起点策略或停止规则。
- 不修改 stage09 至 stage11、CC、LDPC 或公共模块。

## 数据格式

结果以 CSV 保存，明确记录请求长度、实际长度、实际遮挡比例、随机起点范围、整数计数器及 BER/FER/误纠率。
图仅输出 PNG；每张图具有独立 figure-data CSV、SHA-256 manifest。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 固定长度精确生效 | runner `--fixed-length` | 32 点 checker | 长度越界由 runner 拒绝 | 实际长度等于请求长度 |
| 正式停止规则 | runner | 帧数与帧错计数复算 | 帧数上限检查 | 每点满足 5000/200/50000 |
| 结果统计一致 | result CSV | 整数计数复算 | NaN/Inf 和边界检查 | 全部一致 |
| 图与数据可审计 | plot/manifests | 哈希与 PNG 解码 | 禁止 PDF | 6 张图全部通过 |
| 旧实验不回归 | 原 stage12 checker/CTest | 回归执行 | CLI 负向测试 | 全部通过 |

## Gate

32 个正式点、6 张图、C checker、原 stage12 checker 和 CTest 全部通过后，实验 C 功能 Gate 才能标记 PASS。
