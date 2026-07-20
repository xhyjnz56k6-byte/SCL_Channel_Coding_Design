# 指标定义

## BER

```text
BER = payload 错误 bit 数 / payload 总 bit 数
```

BER 只统计 `K_payload` 范围。禁止统计 filler、CRC、tail、parity、punctured placeholder、LDPC filler 或其他辅助位。

## FER

一帧 payload 中只要存在至少 1 个错误 bit：

```text
frameError = true
FER = 错误帧数 / 总帧数
```

## payload 成功率

```text
payloadSuccessRate = 1 - FER
```

它表示最终 payload 完全正确的比例。

## decoder 声明成功率

```text
decoderDeclaredSuccessRate = decoderDeclaredSuccessFrames / totalFrames
```

该指标只表示译码器自己报告成功的比例，不能替代 FER 或 payload 成功率。

## 未检出错误

未检出错误定义为：

```text
decoderDeclaredSuccess = true
AND
payloadError = true
```

字段：

```text
undetectedErrorFrames
undetectedErrorRate = undetectedErrorFrames / totalFrames
```

## 置信区间

默认置信水平：

```text
confidenceLevel = 0.95
```

默认方法：

```text
Wilson score interval
```

字段：

```text
berCiLower
berCiUpper
ferCiLower
ferCiUpper
```

全项目默认只能使用一种置信区间方法。若后续阶段更改方法，必须成阶段冻结并更新所有定义、配置和验证。

## 零错误点

若：

```text
bitErrors = 0
```

CSV 中：

```text
BER = 0
```

若：

```text
frameErrors = 0
```

CSV 中：

```text
FER = 0
```

对数图不能直接绘制 0，因此另设：

```text
plotBER
plotFER
isZeroBitErrorPoint
isZeroFrameErrorPoint
```

允许使用三倍法则近似 95% 上界：

```text
p_upper ~= 3/N
```

该值是显示上界，不是实测 BER/FER。禁止把真实 0 静默替换成 `1e-6` 或绘图下限。

## 编码增益

编码增益是曲线级指标：

```text
G_coding = (Eb/N0)_reference - (Eb/N0)_candidate
```

参考曲线优先使用 uncoded BPSK。目标点优先使用：

```text
FER = 1e-2
```

若双方曲线未覆盖目标点：

```text
codingGain_dB = N/A
```

禁止远距离外推。禁止把 `codingGain_dB` 作为每个 SNR 点的直接测量值。

## 时延范围

至少冻结字段：

```text
avgEncodeTime_us
maxEncodeTime_us
avgDecodeTime_us
maxDecodeTime_us
p95DecodeTime_us
```

可预留字段：

```text
avgInterleaveTime_us
avgDeinterleaveTime_us
avgEndToEndAlgorithmTime_us
```

算法计时不包含文件 IO、日志输出、CSV/JSON 写入、图片绘制、帧池读取、噪声文件读取和配置读取。

极短算法允许 batch timing，但必须记录：

```text
batchSize
totalMeasuredTime
derivedPerFrameTime
```

