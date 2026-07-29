# Stage11 规格冻结：软信息量化

## 目标与范围

在 R12/R23 soft 的四个 Stage10 代表点比较 `SOFT_FLOAT/Q3/Q4/Q6`，先用全局 clipping prescan 冻结单一范围，再给出性能与复杂度推荐。只修改本 Stage 目录。

## 量化合同

- 输入：BPSK `receivedSymbols`，不是 LLR。
- 对称 mid-tread 有符号码，零点为 0。
- b bit 的代码范围 `[-(2^(b-1)-1), +(2^(b-1)-1)]`，保留对称性。
- 步长 `clipMax / codeMax`，舍入到最近整数，饱和上下限为 `±clipMax`。
- punctured bit 使用中性 code=0 且 observedMask=0，不贡献分支度量。
- 分支度量为量化 code 与量化 `±1` 之差平方和。
- 路径度量为 `int32_t`，候选先用 `int64_t` 检测；上限 `1,000,000,000`，每步减去最小有限度量归一化。
- clipping 候选 `{2,3,4,6}`，Q4 在全部四场景各 200 帧联合 prescan；按 float mismatch frames 最少选择，平局取饱和率更低者，不允许逐 SNR 调参。
- 正式：四场景各 1000 帧。
- 推荐：选择所有点 BER/FER 相对 float 增幅均不超过 10%、整数 overflow=0 的最小位宽。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| clipping prescan | C++ runner | 四候选联合比较 | 单点调参禁止 | 单一 clip 冻结 |
| Q3/Q4/Q6 整数 ACS | C++ runner | 无噪声与正式矩阵 | 非法位宽/clip 拒绝 | 无 overflow |
| 性能/复杂度 | checker | BER/FER/时延/吞吐/饱和/内存 | 公式和有限值 mutation | 指标 PASS |
| 推荐位宽 | checker | 最小合格位宽 | 无合格项时拒绝 | 数据化推荐 |

Gate：`PASS_STAGE11_CC_SOFT_QUANTIZATION`
