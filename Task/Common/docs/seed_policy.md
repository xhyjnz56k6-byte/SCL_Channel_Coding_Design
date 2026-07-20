# seed 和噪声公平性定义

## 每帧独立噪声

老师要求冻结为：

```text
每一帧重新生成随机噪声
```

含义：

- 不同 `frameIndex` 的噪声向量不同。
- 同一帧不同码元的噪声样本独立。
- 不能让全部帧重复使用同一条噪声。
- 相同 seed 和上下文下可复现。

本阶段只冻结 seed 派生字段，不实现生成器。

## noiseGroupId

`noiseGroupId` 是公平对比组标识。同一公平对比组内的不同译码算法必须共享同一条标准高斯噪声、同一接收符号或同一 LLR。

卷积码公平比较：

```text
同一 payload
同一码字
同一打孔结果
同一 noiseGroupId
同一标准高斯噪声
同一 receivedSymbols
├─ 硬判决 Viterbi
└─ 软判决 Viterbi
```

LDPC 公平比较：

```text
同一 payload
同一码字
同一 H
同一 noiseGroupId
同一标准高斯噪声
同一 receivedSymbols
同一 LLR
├─ Layered BP
└─ Layered NMS
```

禁止：

- 把 `decoderType` 直接放入噪声 seed。
- 为硬/软 Viterbi 分别重新过信道。
- 为 BP/NMS 分别重新生成 LLR。

## 跨 SNR 策略

默认冻结为：

```text
reuseNoiseAcrossSnr = true
```

含义：

```text
相同 noiseGroupId
相同 frameIndex
不同 Eb/N0 下复用相同标准高斯 z
不同 SNR 只改变 sigma
```

数学形式：

```text
y_{s,f,i} = x_{f,i} + sigma_s*z_{f,i}
```

这不代表所有帧复用同一条噪声；不同 `frameIndex` 的 `z` 仍然不同。

旧规划中“不同 SNR 使用不同噪声流”的说法被本阶段新冻结策略替代，后续实现以 `reuseNoiseAcrossSnr = true` 为准。

## seed 字段边界

正式字段：

```text
masterSeed
noiseGroupId
frameIndex
```

当 `reuseNoiseAcrossSnr = true` 时，`snrIndex` 不进入标准高斯母噪声 seed。

禁止字段：

```text
decoderType
decoderName
algorithmName
```

这些字段不得直接进入噪声 seed。

