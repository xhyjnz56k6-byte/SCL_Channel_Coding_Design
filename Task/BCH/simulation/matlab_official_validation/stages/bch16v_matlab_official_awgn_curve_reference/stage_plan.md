# BCH-16V MATLAB 官方 AWGN 曲线验证规格

## 目标

在 BCH-15 冻结正式配置下，对 BCH-S200 与 BCH-B200 使用相同 Common payload、相同标准高斯母噪声、
相同 Payload Eb/N0、相同实际帧率及相同逐点帧数，实际调用 MATLAB Communications Toolbox
`bchgenpoly`、`bchenc`、`bchdec`，形成 C++ 与 MATLAB 官方 BER/FER 曲线对照。

最终 Gate：`PASS_BCH16V_MATLAB_OFFICIAL_AWGN_CURVE_REFERENCE`。

## 非目标

- 不修改 BCH-15 正式结果、配置和曲线。
- 不修改 BCH 编码器、查表译码器或 BM+Chien 译码器。
- 不使用 MATLAB 自实现 BCH 替代官方函数。
- 不修改 CC、LDPC 或进入 BCH-17 交织实验。
- 不要求超纠错能力范围内 C++ 与 MATLAB 的失败输出策略相同。

## 允许范围

`Task/BCH/simulation/matlab_official_validation/` 下的配置、共享输入导出工具、MATLAB 官方参考、
比较、绘图、审计、测试与本 Stage 记录。

## 禁止范围

旧 Stage、`Task/BCH/simulation/stages/bch15_awgn_formal/`、BCH 核心源码、`Task/CC/`、`Task/LDPC/`。

## 冻结接口与数据格式

- payload：复用 Common03 200-bit packed frame pool，byte 内 `lsb_first`。
- 标准高斯输入：`float64`、little-endian、frame-major，保存未乘 sigma 的 `z ~ N(0,1)`。
- C++ 对照记录：little-endian、每帧 38 byte，仅供结果比较，不作为 MATLAB 算法输入。
- S200：200 payload + 9 尾部 filler，19×BCH(15,11)，285 transmitted bits。
- B200：7 个前置虚拟零 + 200 payload，经 BCH(255,207) 后删除前 7 位，248 transmitted bits。
- `R = payloadLength / encodedLength`；BPSK `0→+1, 1→-1`；硬判决 `<0→1, >=0→0`。
- sigma：`sqrt(1/(2*R*10^(EbN0_dB/10)))`。

## Gate 顺序

1. 第 4 组已进入最新 main，工作区与分支边界合法。
2. MATLAB R2024b / Communications Toolbox 24.2 和三个官方函数可用。
3. 212 个固定编码向量逐 bit 一致。
4. 代表性/正式 hard-decision 帧在保证纠错范围内逐 payload 一致。
5. 完成 35 个正式点、574,743 帧，逐点 processedFrames 相等。
6. 比较、配对统计、四张 PNG、历史回归与最终审计均通过。

