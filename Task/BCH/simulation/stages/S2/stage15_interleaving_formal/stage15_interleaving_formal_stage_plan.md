# Stage15 多交织方式与深度正式实验计划

## 目标

- Stage15-A：8 Case × `NONE/BLOCK/ROW_COLUMN/PSEUDORANDOM` × D=8 × 冻结 L。
- Stage15-B：每个 Case 自动选择最佳必需交织器，比较 NONE 与 D=4/8/16。
- 复用 Stage14 NONE canonical 点和 Stage15-A D=8 点，不重复仿真。
- 输出 FER 改善、突发容限、错误扩散、时延和缓存代价及全部绘图审计资产。

## 边界

- 只修改本 Stage 目录；不修改 Stage01～14、Case contract、BCH 核心或 `Task/Common`。
- 最佳模式只允许从 BLOCK、ROW_COLUMN、PSEUDORANDOM 中自动选择。
- 不实现可选 `CONVOLUTIONAL_EXTENSION`。

## 最佳模式选择

依次比较：冻结 L 上 FER 几何均值、误纠率、容限、附加时延、固定优先级。
所有 tie 和选择分量写入 canonical CSV。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| D=8 方法比较 | runner/finalizer | 8×4×冻结 L | 重复 NONE、缺模式/点 | canonical 点完整 |
| 自动选优 | selector/checker | 三模式确定性排序 | 人工覆盖、选择 NONE | 8 Case 均有可复算选择 |
| 深度比较 | runner/finalizer | NONE+D4/D8/D16 | 重跑 D8、缺深度 | 8 Case 完整 |
| 改善与容限 | checker | 从整数统计复算 | Inf、NaN、伪造缺失点 | 指标一致 |
| 绘图发布 | plot checker | 30 PNG 与逐图资产 | 插值热图、内部 ID 图例 | 全部 hash/点数通过 |

## Gate

`PASS_STAGE15_INTERLEAVING_FORMAL`

