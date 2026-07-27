# stage01_foundation 规格冻结

## 目标

- 收口 BCH S2 的 BPSK/AWGN 数学定义和逐帧随机身份。
- 验证 C++ 与 MATLAB 对固定中立向量的独立计算一致。
- 为后续 Case、trial 和 formal Stage 提供可复用的阶段内基础代码。

## 非目标

- 不定义 8 个正式 Case 的组帧契约。
- 不执行 AWGN trial、prescan 或 formal 仿真。
- 不修改 `Task/Common`、`Task/CC` 或 `Task/LDPC`。

## 冻结接口

随机身份由 `masterSeed, stageId, caseId, ebn0Index, frameIndex, randomDomain`
共同决定。随机域至少包含 `PAYLOAD` 与 `AWGN`。

数学定义：

```text
R = payloadLength / encodedLength
sigma^2 = 1 / (2*R*10^(EbN0_dB/10))
SNR_linear = 1 / sigma^2
SNR_dB = EbN0_dB + 10*log10(2*R)
bit 0 -> +1
bit 1 -> -1
```

## Gate

`PASS_STAGE01_FOUNDATION`

必须满足 CTest 全通过、日志非空、C++/MATLAB 连续量容差通过、离散
mismatch 为零、完整随机身份可复现、frame/case/domain 隔离、resume/shard
不改变逐帧噪声以及文件哈希完整。
