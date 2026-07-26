# S2-05 corrected：残余频偏科学语义修复

## 目标

正式残余 CFO 主实验固定 `initialPhaseDeg=0`，只研究整帧累计旋转；四个初始相位改为独立附加实验。旧 S2-05 数据保留，不覆盖。

## 非目标

不删除旧四相位 formal，不改变 BCH 编译码器，不把整帧累计旋转角解释为跨码一致的物理频偏。

## 范围与数据

- 功能：BCH impairment 信道、runner、测试和 corrected driver。
- 原始结果：`Task/BCH/simulation/results/s2_batch2_corrected/s2_05/`。
- Stage 摘要：本目录三个 CSV。
- 主扫角：`0,5,10,15,20,30,45,60,75,90,120,180`。
- 主扫角每点 5000 帧；三个 AWGN 参考点；五个 BCH Case。
- SNR 扫描：30°/60°，步长 0.2 dB，5000/200/50000 自适应停止。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 主 CFO 固定 φ0=0 | corrected driver | 180 点相位字段检查 | 非零相位污染拒绝 | PASS_BCH_S2_CFO_PHI0_ZERO_CORRECTED |
| 理想补偿等于配对 AWGN | channel + unit test | 样本差≤1e-12、bit/payload一致 | NaN 配置拒绝 | strict compensation Gate |
| 初始相位独立展示 | phase sensitivity CSV | 5×2×4 点 | 禁止聚合为主曲线 | INITIAL_PHASE_SENSITIVITY |

## Gate

`PASS_BCH_S2_CFO_PHI0_ZERO_CORRECTED`
