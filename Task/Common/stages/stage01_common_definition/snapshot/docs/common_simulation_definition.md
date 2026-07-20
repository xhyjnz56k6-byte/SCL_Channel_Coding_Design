# Common-01 公共仿真定义

本文冻结 `SCL_Channel_Coding_Design` 后续公共仿真的数学定义和工程边界。本阶段只定义规则，不实现帧池、随机数、信道、译码器或仿真 runner。

## 长度字段

| 字段 | 定义 | 统计或码率用途 |
|---|---|---|
| `K_payload` | 原始输入电文长度 | BER/FER 只统计该范围；码率分子只使用该字段 |
| `K_codec_input` | 实际进入编码器的信息长度，可包含 filler、CRC、尾比特或适配位 | 不能作为统一码率分子 |
| `N_encoded` | 编码或码率适配后的最终实际编码长度 | 统一码率分母 |
| `N_transmitted` | 实际送入 BPSK 和信道的比特数 | 通常等于 `N_encoded`，但独立保留 |
| `fillerLength` | 码长适配填充位数 | 不计入 payload BER/FER，不增加码率分子 |
| `crcLength` | CRC 位数 | 不增加码率分子 |
| `tailLength` | 卷积码终止尾比特数 | 不增加码率分子 |
| `puncturedLength` | 打孔删除的编码位数 | 分母使用打孔后的实际编码长度 |
| `shortenedLength` | 缩短位数 | 必须单独记录 |

## 统一码率

本项目唯一允许的统一码率定义为：

```text
R = K_payload / N_encoded
```

约束：

- 分子只使用原始 payload 长度。
- filler、CRC、卷积码尾比特和 LDPC filler 不增加分子。
- 分块编码分母使用所有块拼接后的总编码长度。
- 打孔后分母使用打孔后的实际编码长度。
- 禁止使用母码理论码率替代实际仿真码率。
- 禁止使用 `K_codec_input/N_encoded` 或 `Keff/N` 作为项目统一码率。

冻结样例：

| case | `K_payload` | `N_encoded` | `R` |
|---|---:|---:|---:|
| BCH 分块 200 bit | 200 | 285 | 0.7017543859649122 |
| BCH 整块 200 bit | 200 | 248 | 0.8064516129032258 |
| 卷积码 300 bit、1/2 零尾 | 300 | 612 | 0.49019607843137253 |
| LDPC 300 到 480 | 300 | 480 | 0.625 |
| LDPC 300 到 576 | 300 | 576 | 0.5208333333333334 |

## BPSK、AWGN、硬判决和 LLR

BPSK 映射冻结为：

```text
0 -> +1
1 -> -1
```

硬判决规则冻结为：

```text
receivedSymbol >= 0 -> bit 0
receivedSymbol <  0 -> bit 1
```

特别地，`receivedSymbol == 0` 判为 bit 0。

AWGN 模型冻结为：

```text
y = x + sigma*z
z ~ N(0,1)
sigma^2 = 1/(2*R*10^(EbN0_dB/10))
sigma = sqrt(1/(2*R*10^(EbN0_dB/10)))
R = K_payload/N_encoded
```

LLR 约定冻结为：

```text
LLR_i = ln(P(c_i=0|y_i)/P(c_i=1|y_i)) = 2*y_i/sigma^2
LLR > 0 -> 倾向 bit 0
LLR < 0 -> 倾向 bit 1
|LLR| 越大 -> 可靠性越高
```

## 交织位置和启用条件

链路位置冻结为：

```text
编码 -> 交织 -> BPSK -> 信道 -> 解调 -> 去交织 -> 译码
```

基础 AWGN 曲线默认：

```text
interleaverEnabled = false
```

交织只允许同时满足：

```text
channelType = BURST_ERROR
codeType in {BCH, CC}
interleaverEnabled = true
```

LDPC 永远禁止启用交织。若出现：

```text
codeType = LDPC
interleaverEnabled = true
```

定义检查必须判定为非法。

## 输出和防覆盖

点级结果使用 `point_results.csv`，每个 SNR 点一行。

曲线级结果使用 `curve_summary.csv`，编码增益只允许放在曲线级结果中。

元数据使用 `run_metadata.json`。

默认防覆盖策略冻结为：

```text
overwriteExistingResults = false
```

已有正式结果时必须拒绝静默覆盖。

