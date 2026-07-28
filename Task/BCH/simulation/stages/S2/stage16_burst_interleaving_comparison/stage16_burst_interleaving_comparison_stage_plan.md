# Stage16 AWGN+突发适应性与内部综合比较计划

## 目标

- 对 8 个 BCH Case 执行 3 种配置、SNR 0～18 dB、步长 0.5 dB 的正式实验。
- 逐 Case 使用 `actualRate` 将目标 SNR 换算为底层 Eb/N0。
- 自动复用 Stage15 的最佳必需交织器，并自动选择最佳深度和代表性突发长度。
- 汇总 Stage14～Stage16 的突发容限、交织收益、目标 FER SNR、时延和缓存代价。
- 发布 20 张 PNG，每张均配套 figure-data、plot manifest 和 SHA-256。

## 非目标与边界

- 不修改 BCH 编码器、译码器、Case contract、公共随机数、Task/Common 或 Stage01～Stage15。
- 不形成跨 AWGN-only、多径、CFO、遮挡等全部信道的最终排名。
- 不插值原始曲线；目标 FER 只允许在真实覆盖区间内进行对数 FER 域内插值。

## 正式接口

- 点表：`caseId,configurationId,interleaverMode,interleaverDepth,burstLengthIndex,burstLengthBits,snrIndex,targetSnrDb,derivedEbN0Db,permutationSha256`
- 停止规则：`1000 / 200 / 50000 / 1000`
- 配置：`NONE_L0`、`NONE_LREP`、`BEST_LREP`
- 横轴：原始和 figure-data 均使用 `targetSnrDb`，显示标签严格为 `SNR`。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 37 点 SNR 网格 | prepare/runner | 8×3×37 | 缺点、重复点 | 888 点完整 |
| actualRate 换算 | prepare/checker | 逐点复算 | 母码率或统一 Eb/N0 | 误差不超过容差 |
| 代表 L 与最佳交织 | prepare/checker | Stage14/15 重算 | 人工覆盖、选择 NONE | 来源和规则一致 |
| 正式停止与计数 | runner/checker | 两种停止原因 | 超帧、提前停止 | 全点守恒 |
| 门限与推荐 | finalize/checker | 区间内对数插值 | 外推 | 状态和值一致 |
| 图片发布 | plot/checker | 20 组资产 | 非 PNG、内部 ID 图例 | 全部 hash/点数通过 |

## Gate

- `PASS_STAGE16_BURST_INTERLEAVING_COMPARISON`
- `PASS_BCH_S2_BURST_INTERLEAVING_STAGE13_TO_STAGE16`
