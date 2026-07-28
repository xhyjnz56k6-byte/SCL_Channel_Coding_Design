# 打孔图样选择报告

## 冻结结果

- 2/3：`R23_B_1101`，串行 mask `1101`
- 3/4：`R34_B_110110`，串行 mask `110110`

mask 均从独立帧的 mother bit index 0 开始，尾 bit 区域继续当前周期；连续 slot 不重启相位。

## 正确性

四个候选各执行 120 个 300-bit 随机无噪声帧，hard/soft 全部逐 bit 恢复。MATLAB 对每个候选验证打孔输出、terminated hard `vitdec` 和 unquantized soft `vitdec`，mismatch 均为 0。

## 小规模 AWGN 选择

固定 `sigma=0.70`，每候选 120 帧，hard/soft 共享 receivedSymbols。该点用于放大候选差异，不是正式性能结论。

| pattern | hard frame errors | soft frame errors |
|---|---:|---:|
| R23_A_1110 | 119 | 64 |
| R23_B_1101 | 119 | 55 |
| R34_A_111001 | 120 | 110 |
| R34_B_110110 | 120 | 108 |

选择规则依次比较 soft 错误帧、hard 错误帧、稳定 ID。因而冻结 B 图样。此选择只适用于当前 K=7、171/133、300-bit 零尾基准；Stage08 仍需在合理 waterfall 范围验证总体性能。
