# Stage03：AWGN 回归

目标：四方案统一复 AWGN 前端、实轴 LLR 和 CC/LDPC 无噪声回归；MATLAB 官方 `poly2trellis/convenc/vitdec` 核验 CC 编码与译码。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| AWGN LLR | `runChannel` | 三个 Es/N0 fixed vectors | Q 复用 I 拒绝 | 逐元素容差通过 |
| 四方案译码 | `decodeFrame` | identity/noiseless | 长度错拒绝 | 0 payload mismatch |
| CC 官方参考 | MATLAB script | 10 帧 R12/R23 编译码 | 穿孔位序错误 | `PASS_S5_AWGN` |

Gate：`PASS_S5_AWGN`。
