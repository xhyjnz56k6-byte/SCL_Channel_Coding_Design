你的新表述可以成立，但正式报告里必须避免把模型写得过于笼统。

可以在总标题中写：

> **突发信道下交织性能**

但在图注、配置文件和结果表中，必须进一步写明：

> **AWGN 下未知连续 BPSK 极性反转模型**

因为“突发信道”是场景类别，“连续极性反转”才是这次真正采用的信道实现。否则老师以后追问“突发到底是擦除、干扰还是相位翻转”，结果无法复现。

下面先回答固定方案和时延问题，再给出完整 S7 规划。

---

# 一、BCH 和卷积码在突发信道中的统一链路

两类码都采用同一个突发信道定义：

[
y_k=h_kx_k+n_k
]

其中：

[
h_k=
\begin{cases}
-1,&s\le k<s+L\
+1,&\text{其他位置}
\end{cases}
]

[
n_k\sim\mathcal N(0,\sigma^2)
]

即：

```text
编码
→ 交织
→ BPSK
→ 连续一段传输符号极性反转
→ AWGN
→ 接收判决
→ 解交织
→ 译码
```

这里的连续损伤发生在**调制之后的信道中**，而不是提前修改编码 bit。

## 正式命名

项目内部建议写成：

```text
channelType = AWGN_CONTIGUOUS_BPSK_POLARITY_REVERSAL
receiverKnowsBurst = false
burstWrapAround = false
```

中文图题可以简化为：

> 连续突发信道

但图注必须注明：

> 突发区间内 BPSK 符号发生未知极性反转，随后叠加 AWGN。

---

# 二、BCH 和卷积码的判决方式怎样固定

这里不能为了“统一”而让两种码采用相同判决输入。应该保持它们各自正常、合理的接收方式。

---

## 1. BCH：硬判决

BCH 本身是二元代数码，当前工程中的 BCH 译码器接收 0/1 比特，因此链路应为：

```text
接收符号 y
→ BPSK 硬判决
→ 解交织硬比特
→ BCH 查表译码
```

硬判决规则：

[
\hat c_k=
\begin{cases}
0,&y_k\ge0\
1,&y_k<0
\end{cases}
]

交织发生在编码 bit 顺序上；信道中极性反转的是交织后的 BPSK 符号；接收端硬判决以后，必须先解交织，再按照原 BCH 子块边界译码。

---

## 2. 卷积码：软判决

卷积码应保持软判 Viterbi，因为老师要求卷积码支持硬判和软判，而 S7 不是再重复 S6 的译码算法对比，应冻结一个合理主方案。老师文档中也明确指出软判决保留更多可靠性信息，适合评价编码增益和实时性。

链路：

```text
接收符号 y
→ 计算 LLR
→ 对 LLR 解交织
→ 软判 Viterbi
```

LLR：

[
LLR_k=\frac{2y_k}{\sigma^2}
]

其中接收机不知道 (h_k=-1)，仍按普通 AWGN 接收机处理。

必须注意：

> 卷积码解交织的是 LLR 序列，不是先硬判后的 0/1 bit。

---

# 三、S7 应固定哪些 BCH 参数

老师要求低速电文交织测试采用 BCH，并且 BCH(15,11,1) 是低速主推分块方案。

因此 S7 的 BCH 主方案建议固定为：

```text
payloadLength = 200 bit
organization = segmented
componentCode = BCH(15,11,1)
decoder = syndrome lookup
```

现有 S200 结构是：

```text
200 bit 原始电文
→ 补齐到 19×11 = 209 bit
→ 19 个 BCH(15,11,1)
→ 编码后 285 bit
```

有效码率统一按你的定义：

[
R=\frac{\text{原始输入长度}}{\text{编码后发送长度}}
]

所以：

[
R_{\mathrm{BCH}}=\frac{200}{285}\approx0.70175
]

## 为什么固定 S200，而不是整块 BCH

因为 S7 的核心是研究交织如何把连续错误分散到多个独立纠错单元中。

对于 19 个 BCH(15,11,1)：

* 每个子块纠错能力 (t=1)；
* 无交织时连续错误容易集中；
* 交织后可分散到多个子块；
* 机制最直观。

整块 BCH 可以作为补充历史基线，但不应作为 S7 主交织对象。

---

# 四、S7 应固定哪些卷积码参数

老师要求高速电文只保留 300 bit，卷积码母码率 1/2、约束长度 (K=7)、生成多项式 171/133，并支持软判 Viterbi。

因此建议固定：

```text
payloadLength = 300 bit
constraintLength = 7
generators = 171/133 oct
termination = 6 tail bits
rate = mother rate 1/2
decoder = float soft Viterbi
organization = full-block
```

编码后长度：

[
N=2(300+6)=612
]

有效码率：

[
R_{\mathrm{CC}}=\frac{300}{612}\approx0.49020
]

## 为什么不用 R2/3 或 R3/4

因为 S7 要隔离交织影响。

若同时使用打孔码，会额外引入：

* 打孔位置；
* 去打孔零可靠度；
* 码率差异；
* 不同实际发送长度；
* 突发区与打孔图样对齐关系。

这些会干扰交织结论。

所以 S7 主实验应采用未打孔 R1/2。

## 为什么固定整块软判 Viterbi

老师要求卷积码采用短深度块交织，但这不等于必须同时使用滑窗译码。

若同时引入：

* 短深度交织；
* 滑窗长度；
* 滑动步长；
* 回溯深度；

变量会过多。

建议主实验先冻结：

```text
full-block soft Viterbi
traceback policy = 现有正式推荐值
```

若后续需要体现实时高速处理，再增加一个小规模扩展：

```text
short-depth interleaver
+ frozen sliding-window Viterbi
```

但不作为主 Formal。

---

# 五、BCH 和卷积码的交织方式固定

老师要求：

* BCH：无交织、块交织、行列交织、伪随机交织；
* 卷积码：无交织、短深度块交织、伪随机交织。

---

## BCH 四种

```text
NONE
BCH_CODEBLOCK
ROW_COLUMN
GLOBAL_PSEUDORANDOM
```

### NONE

恒等映射。

### BCH_CODEBLOCK

按 BCH 子码字结构交织。

深度：

```text
D_BCH = 4、8、16、19
```

其中 (D_{\mathrm{BCH}}) 表示一次参与交织的 BCH(15,11,1) 子块数量。

### ROW_COLUMN

对整个 285 bit 编码帧进行矩形行列交织。

候选行数：

```text
rows = 4、8、15、19
```

最终通过预扫描选出一个代表参数进入全 SNR Formal。

### GLOBAL_PSEUDORANDOM

对 285 bit 全帧使用固定伪随机置换。

记录：

```text
spanBits = 285
seed
permutationHash
```

不再称为 `depth=4/8/16`。

---

## 卷积码三种

```text
NONE
SHORT_DEPTH_BLOCK
LOCAL_OR_GLOBAL_PSEUDORANDOM
```

### SHORT_DEPTH_BLOCK

建议按 trellis 时刻组织，而不是任意拆散同一时刻的两个母码输出。

一个 trellis 时刻：

[
S_t=[c_{t,0},c_{t,1}]
]

候选：

```text
D_int = 4、8、16
C_int = 8
```

一次缓存：

[
D_{\mathrm{int}}C_{\mathrm{int}}
]

个 trellis 时刻。

对应编码 bit 缓冲量：

[
2D_{\mathrm{int}}C_{\mathrm{int}}
]

即：

| 参数         | trellis 时刻 | 编码 bit |
| ---------- | ---------: | -----: |
| (D=4,C=8)  |         32 |     64 |
| (D=8,C=8)  |         64 |    128 |
| (D=16,C=8) |        128 |    256 |

### PSEUDORANDOM

卷积码建议采用局部伪随机 trellis 时刻置换，而不是任意打乱 612 个单 bit。

候选跨度：

```text
32、64、128 个 trellis 时刻
```

每个 (S_t) 内的两个母码输出保持成组。

正式方法比较可以选一个经过预扫描的代表跨度。

---

# 六、必须输出纯译码时间 (T_{\text{decode}})

这一点完全同意，而且必须独立统计。

## BCH

计时范围：

```text
解交织后的硬比特已准备完毕
→ 调用 BCH 译码函数
→ 输出恢复 payload 和译码状态
```

定义：

[
T_{\mathrm{decode,BCH}}
=======================

t_{\mathrm{decode,end}}-t_{\mathrm{decode,start}}
]

统计：

```text
mean
median
P95
P99
max
```

---

## 卷积码

计时范围：

```text
解交织后的 LLR 已准备完毕
→ 调用 soft Viterbi
→ 输出 300 bit payload
```

定义：

[
T_{\mathrm{decode,CC}}
======================

t_{\mathrm{decode,end}}-t_{\mathrm{decode,start}}
]

同样统计：

```text
mean
median
P95
P99
max
```

S5 已经采用了从 LLR 到译码 payload/status 的计时范围，并通过 `steady_clock` 统计平均、中位数、P95 和最大值，这个计时框架值得直接复用。

---

# 七、没有符号率和采样率，附加时延到底怎样统计

这是必须纠正口径的地方。

当前工程没有：

* 符号率；
* bit rate；
* 采样率；
* 每符号采样点数。

因此，**不能把交织缓冲等待直接换算成秒、毫秒或微秒**。

只能输出两类时延。

---

## 1. 实测算法执行时间

可以用 CPU 时钟测量：

[
T_{\mathrm{interleave,cpu}}
]

[
T_{\mathrm{deinterleave,cpu}}
]

[
T_{\mathrm{decode}}
]

[
T_{\mathrm{receiver,cpu}}
=========================

T_{\mathrm{deinterleave,cpu}}
+
T_{\mathrm{decode}}
]

这些可以用：

```text
ns
μs
```

报告，因为它们是程序运行时间，与符号率无关。

---

## 2. 归一化缓冲等待量

交织器需要等待一定数量的编码 bit 或 trellis 时刻，才能产生可供后续处理的数据。

没有传输速率时，应报告：

```text
startupDelayBits
startupDelayCodedSymbols
startupDelayTrellisSteps
bufferBits
bufferFractionOfFrame
```

而不能直接报告：

```text
startupDelayUs
```

### BCH 示例

全帧伪随机交织：

```text
startupDelayBits = 285
bufferBits = 285
bufferFractionOfFrame = 1
```

BCH 局部码块交织 (D=4)：

```text
startupDelayBits ≈ 4×15 = 60
bufferBits ≈ 60
bufferFractionOfFrame = 60/285
```

### 卷积码示例

短深度块交织 (D=8,C=8)：

```text
startupDelayTrellisSteps = 64
startupDelayBits = 128
bufferBits = 128
bufferFractionOfFrame = 128/612
```

---

## 3. 附加时延的正式定义

当前工程建议定义两个字段。

### 算法附加时延

[
T_{\mathrm{add,cpu}}
====================

T_{\mathrm{interleave,cpu}}
+
T_{\mathrm{deinterleave,cpu}}
]

单位：

```text
ns 或 μs
```

### 结构附加等待量

[
D_{\mathrm{buffer}}
===================

\text{首次能够输出所需等待的编码 bit 数}
]

单位：

```text
coded bits
```

正式报告中可以写：

> 由于当前离散 BPSK 链路未定义符号率和采样率，交织缓冲引入的等待时延以编码 bit 数和帧比例报告，不换算为物理时间；仅交织、解交织和译码的程序执行时间以微秒统计。

这是最严谨的口径。

---

# 八、S7 完整实验目标

S7 不重新比较各种码长和各种译码算法，而是：

> 固定代表性 BCH 和卷积码方案，量化交织方法、交织参数、突发长度和突发位置对 BER、FER、突发容限和处理代价的影响。

老师要求的主输出是：

```text
突发错误容限
FER 改善
附加时延
```

且交织结果必须单独汇总。

---

# 九、S7 完整实验矩阵

## A. 编码方案

### BCH

```text
BCH-S200
K_payload = 200
19 × BCH(15,11,1)
N_tx = 285
R = 200/285
查表译码
硬判决
```

### 卷积码

```text
CC-R1/2
K_payload = 300
K_constraint = 7
G = 171/133 oct
tail = 6
N_tx = 612
R = 300/612
浮点软判 Viterbi
```

### LDPC

```text
不配置交织
只保留一条无交织历史基线
不进入交织收益排名
```

---

## B. 信道模型

主 Formal：

```text
AWGN
+
未知连续 BPSK 极性反转
```

公式：

[
y_k=h_kx_k+n_k
]

突发区间内：

[
h_k=-1
]

接收机未知。

正式报告中总称：

> 突发信道

子模型名：

> AWGN 下未知连续 BPSK 极性反转。

---

## C. SNR 网格

统一：

```text
Es/N0 = -5～10 dB
step = 0.5 dB
31 points
```

噪声：

[
\sigma^2
========

\frac{1}{2\cdot10^{E_s/N_0/10}}
]

---

## D. 突发比例

正式扫描：

```text
2%
5%
10%
```

实际长度：

[
L=\operatorname{round}(\rho N)
]

### BCH (N=285)

| 比例  |   突发长度 |
| --- | -----: |
| 2%  |  6 bit |
| 5%  | 14 bit |
| 10% | 29 bit |

### 卷积码 (N=612)

| 比例  |                突发长度 |
| --- | ------------------: |
| 2%  | 12 symbol positions |
| 5%  | 31 symbol positions |
| 10% | 61 symbol positions |

这里卷积码一个发送位置就是一个 BPSK 编码 bit，所以也可记录为 12、31、61 coded symbols。

---

## E. 突发位置

正式六种：

```text
HEAD
QUARTER
MIDDLE
THREE_QUARTER
TAIL
RANDOM
```

定义：

[
s_{\mathrm{head}}=0
]

[
s_{\mathrm{quarter}}
====================

\operatorname{round}\frac{N-L}{4}
]

[
s_{\mathrm{middle}}
===================

\operatorname{round}\frac{N-L}{2}
]

[
s_{\mathrm{threeQuarter}}
=========================

\operatorname{round}\frac{3(N-L)}{4}
]

[
s_{\mathrm{tail}}=N-L
]

随机起点：

[
s\sim U{0,\ldots,N-L}
]

必须保持：

```text
noWrap = true
```

---

## F. 停止规则

正式统一：

```text
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
checkpointIntervalFrames = 1000
```

---

## G. 严格成对停止

同一个：

```text
code
burst ratio
burst position
Es/N0
frameIndex
```

下，所有交织方式共享：

* payload；
* 高斯噪声；
* 突发位置；
* 突发长度；
* frame 范围。

停止条件建议为：

> 同一比较组中的所有交织方案都满足目标错误帧数后共同停止，或共同达到最大帧数。

S5 已经实现了成对停止并在合并审计中检查对比方案帧数一致，这一机制应扩展为 S7 的多方案组停止。 

---

# 十、实验阶段规划

## Stage01：仓库与旧结果审计

* 检查分支、工作树；
* 扫描 S2 Stage13～16；
* 扫描 S3 卷积码实现；
* 扫描 S5 连续损伤和成对停止框架；
* 归档旧 S2 交织结果；
* 标记旧 `BLOCK` 为 `LEGACY_ROTATING_BLOCK`；
* 不删除旧结果。

---

## Stage02：S7 参数与术语冻结

生成：

```text
s7_formal_frozen_config.json
S7_DEFINITIONS.md
S7_CHANNEL_MODEL.md
```

冻结：

* 编码方案；
* 码率定义；
* 突发模型；
* 交织方式；
* 突发比例；
* 起点定义；
* SNR；
* 停止规则；
* 时延口径；
* 结果字段。

---

## Stage03：交织器重构

BCH：

```text
NONE
BCH_CODEBLOCK
ROW_COLUMN
GLOBAL_PSEUDORANDOM
```

卷积码：

```text
NONE
SHORT_DEPTH_BLOCK
PSEUDORANDOM
```

验证：

```text
正逆互逆
无重复索引
无缺失索引
无越界
输入输出长度不变
固定 seed 可复现
mapping hash 稳定
```

---

## Stage04：突发信道实现

实现：

```text
h[k] = -1 inside burst
h[k] = +1 outside burst
y[k] = h[k] x[k] + n[k]
```

验证：

* (L=0) 等价 AWGN；
* (L=N) 全帧反转；
* 突发不越界；
* 五个固定起点准确；
* 随机起点可复现；
* 不同交织器共享相同传输位置。

---

## Stage05：BCH 接收链路

```text
BPSK接收
→ 硬判决
→ 解交织
→ 19个BCH子块查表译码
→ 去除padding
```

新增统计：

```text
affectedBlocks
maxErrorsInOneBlock
uncorrectableBlockCount
miscorrectionFrames
undetectedErrorFrames
```

---

## Stage06：卷积码接收链路

```text
BPSK接收
→ LLR
→ 解交织LLR
→ soft Viterbi
→ 去尾bit
→ 恢复300 bit payload
```

检查：

* 同一 trellis 时刻的输出组织；
* 解交织后 LLR 长度 612；
* 无突发无噪声零误码；
* NONE 与历史 R1/2 基线一致。

---

## Stage07：固定向量与单元测试

测试：

```text
无噪声无突发
无噪声全帧反转
单点突发
帧首
帧尾
跨块边界
矩阵余数区
固定随机seed
```

Gate：

```text
roundTripMismatch = 0
noiselessNoBurstErrors = 0
duplicateIndex = 0
missingIndex = 0
outOfRange = 0
sharedNoiseMismatch = 0
sharedBurstMismatch = 0
```

---

## Stage08：交织参数预扫描

### BCH

* `BCH_CODEBLOCK`: (D=4,8,16,19)
* `ROW_COLUMN`: rows (=4,8,15,19)
* `GLOBAL_PSEUDORANDOM`: 固定全帧

### 卷积码

* `SHORT_DEPTH_BLOCK`: (D=4,8,16,\ C=8)
* `PSEUDORANDOM`: span (=32,64,128) trellis steps

预扫描仅用于选 Formal 代表参数。

选取原则：

```text
FER 改善
最坏位置 FER
bufferBits
T_deinterleave
```

不能只选 FER 最低者。

---

## Stage09：位置边界专项实验

必须覆盖：

```text
帧首
1/4
帧中
3/4
帧尾
随机
矩阵边界
局部交织组边界
末尾余数区
```

代表突发比例：

```text
2%、5%、10%
```

输出：

```text
平均FER
最坏FER
最好FER
最坏位置
边界位置FER
位置敏感度
```

---

## Stage10：BCH Formal

完整：

```text
31 SNR
× 3 burst ratios
× 6 positions
× 4 interleaver modes
```

但深度参数先在 Stage08 冻结，不在 Formal 中重复展开全部候选。

---

## Stage11：卷积码 Formal

完整：

```text
31 SNR
× 3 burst ratios
× 6 positions
× 3 interleaver modes
```

使用：

```text
R1/2
full-block float soft Viterbi
```

---

## Stage12：全起点专项遍历

选代表 SNR：

```text
低、中、高三个工作点
```

选代表突发比例：

```text
5%
10%
```

遍历：

[
s=0,\ldots,N-L
]

输出：

```text
失败起点比例
最坏起点
最好起点
边界起点
位置FER热力图
```

不必对所有 31 个 SNR 做全起点遍历。

---

## Stage13：时延与复杂度统计

必须输出：

### 纯译码

```text
T_decode_mean
T_decode_median
T_decode_p95
T_decode_p99
T_decode_max
```

### 交织处理

```text
T_interleave_cpu
T_deinterleave_cpu
T_add_cpu
```

其中：

[
T_{\mathrm{add,cpu}}
====================

T_{\mathrm{interleave,cpu}}
+
T_{\mathrm{deinterleave,cpu}}
]

### 缓冲等待

```text
bufferBits
startupDelayBits
bufferFractionOfFrame
startupDelayTrellisSteps
```

明确不换算为秒。

---

## Stage14：FER 改善计算

定义：

### 绝对改善

[
\Delta FER_{\mathrm{abs}}
=========================

FER_{\mathrm{none}}-FER_{\mathrm{int}}
]

### 相对改善

[
\Delta FER_{\mathrm{rel}}
=========================

\frac{FER_{\mathrm{none}}-FER_{\mathrm{int}}}
{FER_{\mathrm{none}}}
]

### 改善倍数

[
G_{\mathrm{FER}}
================

\frac{FER_{\mathrm{none}}}{FER_{\mathrm{int}}}
]

### 目标 FER 下 SNR 改善

[
G_{\mathrm{SNR}}
================

SNR_{\mathrm{none}}-SNR_{\mathrm{int}}
]

只在可插值区间内报告。

---

## Stage15：科研绘图

BCH 图：

1. FER—Es/N0；
2. BER—Es/N0；
3. FER 绝对改善—Es/N0；
4. FER 相对改善—Es/N0；
5. 六位置 FER；
6. 最坏位置 FER；
7. 位置敏感度；
8. FER—突发比例；
9. 最大单块错误数；
10. 受影响 BCH 块数；
11. FER—bufferBits；
12. (T_{\text{decode}})；
13. 交织 CPU 附加时延；
14. 全起点热力图。

卷积码图：

1. FER—Es/N0；
2. BER—Es/N0；
3. FER 绝对改善；
4. FER 相对改善；
5. 六位置 FER；
6. 最坏位置 FER；
7. FER—短深度参数；
8. FER—伪随机跨度；
9. (T_{\text{decode}})；
10. (T_{\text{deinterleave}})；
11. bufferBits；
12. 全起点热力图。

全部中文标题、横纵轴和图例。

---

## Stage16：结果审计与最终汇总

检查：

```text
完整点数
无重复
无缺失
BER/FER与计数一致
共享帧一致
共享噪声一致
共享突发位置一致
成组帧数一致
无NaN/Inf
时延字段完整
结果哈希完整
```

最终汇总表必须包括老师要求的：

* 编码后码长；
* 有效码率；
* 平均译码时延；
* 最大译码时延；
* 交织设置；
* 推荐适用场景。

并新增：

* 突发比例；
* 最坏位置 FER；
* FER 改善；
* bufferBits；
* 交织附加 CPU 时间；
* 推荐交织参数。

---

# 十一、最终冻结建议

## BCH

```text
BCH-S200
200 bit
19×BCH(15,11,1)
N=285
硬判决
查表译码
```

## 卷积码

```text
CC R1/2
300 bit
K=7
171/133
6 tail
N=612
浮点软判 Viterbi
```

## 突发信道

```text
AWGN下未知连续BPSK极性反转
2%、5%、10%
六种位置
```

## 时延

```text
T_decode 必须单独输出
交织/解交织 CPU 时间单独输出
缓冲等待只用 coded bits / trellis steps 表示
不伪造物理时间
```

## 结果结论

只围绕三件事：

```text
能容忍多长的连续突发
FER到底改善多少
为此付出多少缓冲和处理代价
```

这套规划既符合老师 S7 的直接要求，也修复了 S2 中块交织定义、伪随机深度和突发位置覆盖不足的问题。
