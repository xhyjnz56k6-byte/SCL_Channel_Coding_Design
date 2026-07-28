# CC S3 冻结合同

## 基础参数

正式主场景固定为 300 bit payload。200 bit 仅用于接口兼容和边界测试，不得用于正式性能结论。

| 名称 | 冻结值 |
|---|---:|
| `payloadLength` | 300 bit |
| `constraintLength` | 7 |
| `memory` | 6 |
| `stateCount` | 64 |
| `motherRateNumerator` | 1 |
| `motherRateDenominator` | 2 |
| `generator1Octal` | 171 |
| `generator2Octal` | 133 |
| `initialState` | 0 |
| `tailLength` | 6 |
| `modulation` | BPSK |
| `baselineChannel` | AWGN |

## 长度定义

- `K_payload`：原始 payload 长度，BER/FER 的唯一统计范围，也是实际码率的唯一分子。
- `K_codec_input`：进入卷积编码器的输入长度。整块零尾场景为 `K_payload + tailLength`。
- `N_mother`：未打孔母码输出 bit 数，等于 `2 * K_codec_input`。
- `N_transmitted`：打孔后实际送入 BPSK 和信道的 bit 数，由程序逐 bit 统计。
- `puncturedLength`：`N_mother - N_transmitted`。

整块 300 bit 零尾基准：

```text
K_payload = 300
tailLength = 6
K_codec_input = 306
N_mother = 612
N_transmitted = 612
actualRate = 300 / 612 = 0.49019607843137253
```

统一实际码率：

```text
actualRate = K_payload / N_transmitted
codeRate = actualRate
```

`codeRate` 仅作为 `Task/Common` schema 兼容镜像，二者必须逐行相等。禁止用理论母码率 1/2 替代 `actualRate`。

## 整块终止

整块编码从 state 0 开始，在 payload 后追加恰好 6 个值为 0 的尾 bit。编码结束状态必须为 0。译码器对 306 个 trellis 输入时刻进行回溯，强制终止状态为 0，随后删除最后 6 个尾 bit，只输出 300 bit payload。

## BPSK、硬判决和 LLR

```text
bit 0 -> +1.0
bit 1 -> -1.0
y >= 0 -> hard bit 0
y <  0 -> hard bit 1
LLR = 2*y/sigmaSquared
LLR > 0 -> 倾向 bit 0
LLR < 0 -> 倾向 bit 1
```

`y == 0` 必须硬判为 bit 0。

## SNR 定义

所有正式 AWGN 图横轴的 `SNR (dB)` 固定表示归一化 BPSK 发送符号的 `Es/N0`。对每个结果点：

```text
snrDb = ebN0Db + 10*log10(actualRate)
ebN0Db = snrDb - 10*log10(actualRate)
sigmaSquared = 1/(2*10^(snrDb/10))
sigma = sqrt(sigmaSquared)
```

CSV/JSON 必须同时记录 `snrDb`、`ebN0Db`、`actualRate`、`sigmaSquared` 和 `sigma`。checker 必须逐点复算，禁止把 `snrDb` 同时当作 `Eb/N0`。

## 公平随机链路

同一公平组必须共享：

```text
payload
-> mother codeword
-> punctured codeword
-> BPSK symbols
-> standard Gaussian noise
-> receivedSymbols
   |-> hardBits -> hard Viterbi
   `-> receivedSymbols/LLR -> soft Viterbi
```

相同 `masterSeed`、`noiseGroupId` 和 `frameIndex` 必须复现相同标准高斯噪声；不同 `frameIndex` 必须使用独立噪声向量。SNR 只改变 `sigma`，不改变标准高斯母噪声。不得为 hard/soft 单独生成噪声。

## BER、FER 和停止规则

```text
BER = payloadBitErrors / (framesProcessed * K_payload)
FER = payloadErrorFrames / framesProcessed
payloadSuccessRate = 1 - FER
normalizedGoodput = actualRate * (1 - FER)
```

只统计原始 payload，不统计 6 个尾 bit、打孔缺失位或内部状态。

正式停止规则：

```text
minFrames = 5000
targetFrameErrors = 200
maxFrames = 50000
checkpointIntervalFrames = 1000

(framesProcessed >= minFrames AND payloadErrorFrames >= targetFrameErrors)
OR
framesProcessed >= maxFrames
```

允许的停止原因：

```text
TARGET_ERRORS_REACHED
MAX_FRAMES_REACHED
ERROR_ABORT
MANUAL_STOP
```

prescan 固定默认值为 300、30、2000，SNR 步长 0.5 dB。

## 计时边界

正式计时使用 Release 构建、预热和 batch timing。编码、译码分别计时，不包含文件 IO、日志、CSV/JSON、绘图、配置读取、帧池读取、随机 payload 生成或噪声生成。

## 防覆盖

正式结果默认 `overwriteExistingResults=false`。checkpoint、分片和合并不得重复帧、跳帧或静默覆盖既有结果。
