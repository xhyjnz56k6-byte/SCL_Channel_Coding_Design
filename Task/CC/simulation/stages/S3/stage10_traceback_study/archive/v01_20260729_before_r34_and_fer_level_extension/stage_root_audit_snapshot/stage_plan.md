# Stage10 规格冻结：回溯深度研究

## 目标

在 1/2 soft 与 2/3 soft 的瀑布区代表点比较 `Dtb={35,49,70}` 和完整块已知零终止回溯，量化性能、时延、survivor 内存和回溯操作数，并由数据冻结后续滑窗推荐 Dtb。

## 非目标

- 不替换 Stage09 正式曲线。
- 不在本 Stage 实现分块流水线。
- 不把“常用 5K”作为无实验依据的结论。

## 范围

只修改 `Task/CC/simulation/stages/S3/stage10_traceback_study/`。Stage09 及公共编译码实现只读复用。

## 冻结语义

- Case/SNR：R12-soft {-0.5, 0.0} dB；R23-soft {0.5, 1.0} dB。
- 每点 1000 帧，复用 masterSeed=2026072001、公共 payload 和母噪声。
- 完整块基准：处理 306 个 codec input 后从已知 finalState=0 回溯全部 306 步。
- 有限回溯：处理中间时刻从当前最优状态回溯 Dtb；块末最后 Dtb 位利用已知 finalState=0 flush。它是“有限回溯输出”，不是 Stage12 的滑窗调度实现。
- `survivorMemoryBytes = Dtb * 64 * sizeof(Survivor)`；完整块用 306 步。
- `tracebackOperations` 记录逐帧实际 survivor 访问次数。
- 单帧 `firstStableOutputDepth` 定义为候选集合中第一个与完整块 payload 完全一致的 Dtb；若三者均不一致则为 306。结果表记录帧均值。
- 推荐优先门限为所有点 BER/FER 增幅均不超过 5%；若无候选达到，则允许明确标注 `FALLBACK`，要求最坏 BER 增幅不超过 10%、最坏 FER 增幅不超过 15%，且 survivor 内存至少减少 50%。若 fallback 仍无候选则 Gate 失败。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 三候选与完整块对比 | C++ runner | 4 场景×4 模式 | 非法 Dtb/长度拒绝 | 全矩阵完成 |
| 性能与 mismatch | runner + checker | BER/FER/差异公式 | 计数越界拒绝 | 公式 PASS |
| 时延/内存/操作数 | runner | finite/p95/max/内存公式 | NaN/Inf 拒绝 | 指标 PASS |
| 数据化推荐 | checker | 依门限选择最小合格 Dtb | 无合格候选时拒绝伪选 | 推荐可追溯 |
| 审计 | manifest | functional range 对齐 | 越界拒绝 | 审计 PASS |

## Gate

`PASS_STAGE10_CC_TRACEBACK_STUDY`
