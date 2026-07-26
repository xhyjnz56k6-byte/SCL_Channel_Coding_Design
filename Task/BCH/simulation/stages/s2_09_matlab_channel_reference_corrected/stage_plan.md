# S2-09 corrected：MATLAB 独立 CFO 对照

## 目标

独立复算 corrected residual CFO 与初始相位附加实验的接收样本、理想补偿、硬判决、payload 和帧错误。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| corrected CFO MATLAB | corrected exporter + MATLAB script | 15组×100帧 | 样本差>1e-12拒绝 | PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE |
| 初始相位 MATLAB | 同上 | 20组×100帧 | 任一离散 mismatch拒绝 | PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE |

## Gate

`PASS_BCH_S2_CORRECTED_MATLAB_REFERENCE`
