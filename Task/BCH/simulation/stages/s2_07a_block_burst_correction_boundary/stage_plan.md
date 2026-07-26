# S2-07A 规格冻结

## 目标

整块 BCH 连续硬 bit 翻转的确定性全起点纠错边界。

## 非目标

不包含 AWGN、遮挡、脉冲噪声、波形域干扰或完整物理突发信道建模；不修改 BCH 编译码算法和历史结果。

## 数据模型

编码后硬判决 bit 序列上注入连续翻转：`r = c XOR e`。确定性枚举与随机 Monte Carlo 分开记录。

## Gate

`PASS_BCH_S2_07A_BLOCK_BURST_CORRECTION_BOUNDARY`
