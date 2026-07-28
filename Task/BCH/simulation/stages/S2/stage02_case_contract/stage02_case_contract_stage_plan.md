# stage02_case_contract 规格冻结

## 目标

冻结 8 个 BCH Case 的合法组帧、实际发送长度、码率、译码器、恢复顺序、图例和样式。

K300_M255K207 固定为两个等长缩短码块：每块承载 150 bit，向 BCH(255,207)
母码前置 57 个已知零缩短位，每块发送 198 bit，总发送长度 396 bit。

## 非目标

- 不执行带噪声实验。
- 不修改既有 BCH 编解码核心。
- 不通过 Case 名称在运行时隐式推导长度或母码参数。

## Gate

`PASS_STAGE02_CASE_CONTRACT`

8 个 Case 必须全部通过长度、码率、编码恢复、MATLAB 数学参考、唯一图例和唯一
payload 内样式检查；非法 Case、payload 长度和接收长度必须拒绝。
