# S2-08 corrected：严格阈值、科研绘图与多信道比较

## 目标

使用 φ0=0 corrected CFO，严格分类 CFO/遮挡/burst 容忍区间，补齐 burst 理论 Gate，拆分多信道图并审计时延。

## 非目标

不覆盖旧 S2-06/S2-07 原始结果，不构造跨物理量加权总分，不把测试上限当精确临界值。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 严格 tolerance | corrected driver | observed bracket/limit 分类 | 禁止 max(valid) 冒充阈值 | PASS_BCH_S2_STRICT_TOLERANCE_CLASSIFICATION |
| burst 保证区间 | corrected results/s2_07 | 192 点、960000 帧 | 任一帧错误立即 BLOCKED | PASS_BCH_S2_BURST_THEORY_GATE |
| 科研绘图 | corrected plot script | 22 PNG + figure-data + hash | 非 PNG/缺失数据拒绝 | PASS_BCH_S2_CORRECTED_PLOT_AUDIT |
| corrected 多信道比较 | corrected compare script | 仅 observed bracket 插值 | 禁止外推和旧 CFO | PASS_BCH_S2_CORRECTED_CHANNEL_COMPARISON |
| 时延拆分 | timing-only rerun | decode/preprocess/total P50/P95 | 不替换 BER/FER | PASS timing audit |

## Gate

`PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION_SCIENTIFIC_GATE`
