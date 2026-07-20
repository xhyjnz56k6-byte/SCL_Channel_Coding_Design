# BCH 仿真实验完整实施计划

下面这套方案将 BCH 部分拆成一条**分块主线**、一条**整块缩短对比主线**，再统一进入 AWGN、复杂信道、交织、时延、复杂度和编码增益分析。

老师文档已经明确：低速电文只采用 BCH；BCH(15,11,1) 是主推分块方案；200 bit 和 300 bit 还要分别与整块缩短 BCH 对比；交织是独立测试项，不属于 BCH 的默认链路。fileciteturn3file0

---

# 一、BCH 阶段最终要回答的问题

BCH 仿真不能只做到“编码、译码能运行”，最终要回答：

1. 对 200 bit 和 300 bit 低速电文，BCH(15,11,1) 分块后需要多少组、多少 filler、发送多少 bit。
2. BCH(15,11,1) 的单块纠错能力如何传递到完整 200/300 bit 电文的 FER。
3. 分块 BCH 与整块缩短 BCH 谁的 BER、FER 更好。
4. 整块 BCH 增加的 GF 运算、BM、Chien 搜索复杂度，是否换来了足够的性能收益。
5. 不同 BCH 方案在 AWGN、突发错误、遮挡、多径等条件下的差异。
6. 交织能否把集中错误分散到不同 BCH 小块中，并降低整帧 FER。
7. 各方案的编码后长度、有效码率、平均/最大时延、编码增益和实现复杂度。
8. 最终给出 200 bit 与 300 bit 低速电文的工程推荐方案。

---

# 二、BCH 总体实验对象

## 2.1 主线 A：分块 BCH

```text id="tbxk8k"
BCH(15,11,1)
生成多项式：g(x)=x^4+x+1
系统编码
syndrome 查表译码
纠错能力：t=1
```

## 2.2 主线 B：整块缩短 BCH

```text id="a3g72w"
200 bit：
母码 BCH(255,207)
缩短后计划得到 (248,200)

300 bit：
母码 BCH(511,421)
缩短后计划得到 (390,300)

扩展：
BCH(511,385) 的缩短方案
```

老师文档给出的 BCH 主方案和两个整块对比码长分别是 15 bit/组、248 bit 和 390 bit。fileciteturn2file17

但有一点必须特别注意：

> `BCH(255,207)`、`BCH(511,421)` 和 `BCH(511,385)` 在正式编码前，必须重新核对母码参数、生成多项式、有限域定义和纠错能力 \(t\)。不能仅凭文档中的名称直接开始写 BM 译码器。

因此整块 BCH 必须先经过独立的“参数冻结 Stage”。

---

# 三、固定实验 Case

## 3.1 基础四个主 Case

| Case ID | Payload | 方案 | 发送长度 \(N_{\mathrm{tx}}\) | 有效码率 |
|---|---:|---|---:|---:|
| BCH-S200 | 200 | BCH(15,11,1) 分块 | 285 | 0.70175 |
| BCH-S300 | 300 | BCH(15,11,1) 分块 | 420 | 0.71429 |
| BCH-B200 | 200 | 缩短 BCH(255,207) | 248 | 0.80645 |
| BCH-B300 | 300 | 缩短 BCH(511,421) | 390 | 0.76923 |

其中：

\[
R_{\mathrm{eff}}=\frac{K_{\mathrm{payload}}}{N_{\mathrm{tx}}}
\]

## 3.2 扩展 Case

| Case ID | Payload | 方案 | 定位 |
|---|---:|---|---|
| BCH-B300X | 300 | BCH(511,385) 缩短 | 可选扩展对比 |
| UNC-200 | 200 | 未编码 BPSK | 编码增益参考 |
| UNC-300 | 300 | 未编码 BPSK | 编码增益参考 |

---

# 四、分块 BCH 的准确参数

## 4.1 200 bit

\[
B_{200}=\left\lceil\frac{200}{11}\right\rceil=19
\]

\[
K_{\mathrm{fill}}=19\times11-200=9
\]

\[
N_{\mathrm{tx}}=19\times15=285
\]

\[
R_{\mathrm{eff}}=\frac{200}{285}\approx0.70175
\]

完整含义：

```text id="4i809b"
原始 payload：200 bit
尾部补 9 个 0
形成 209 bit 编码器输入
分成 19 个 11 bit 小块
每块编码成 15 bit
最终发送 285 bit
译码后只保留前 200 bit
```

## 4.2 300 bit

\[
B_{300}=\left\lceil\frac{300}{11}\right\rceil=28
\]

\[
K_{\mathrm{fill}}=28\times11-300=8
\]

\[
N_{\mathrm{tx}}=28\times15=420
\]

\[
R_{\mathrm{eff}}=\frac{300}{420}\approx0.71429
\]

完整含义：

```text id="n9sx3d"
原始 payload：300 bit
尾部补 8 个 0
形成 308 bit 编码器输入
分成 28 个 11 bit 小块
每块编码成 15 bit
最终发送 420 bit
译码后只保留前 300 bit
```

已有参数计划同样将 200/300 bit 分块情况冻结为 19/28 组、9/8 个 filler 和 285/420 bit 输出。fileciteturn3file2

---

# 五、统一数据链路

## 5.1 基础 AWGN 链路

```text id="ns96fw"
公共 payload 帧
      ↓
分组或缩短适配
      ↓
BCH 编码
      ↓
BPSK：0→+1，1→−1
      ↓
AWGN
      ↓
硬判决
      ↓
BCH 译码
      ↓
去 filler / 去缩短位
      ↓
恢复 payload
      ↓
统计 BER、FER、成功率和时延
```

BCH 主实验默认使用**硬判决**，因为：

- BCH(15,11,1) 的 syndrome 查表译码输入是 15 bit 硬比特；
- 整块 BM/Chien 译码通常也是基于硬判决码字；
- 本项目对卷积码和 LDPC 才重点使用软信息译码。

## 5.2 AWGN 方差

\[
\sigma^2=
\frac{1}
{2R_{\mathrm{eff}}10^{E_b/N_0/10}}
\]

\[
y_i=x_i+\sigma z_i,\qquad z_i\sim\mathcal N(0,1)
\]

注意：

- 每种 BCH Case 使用自己的 \(R_{\mathrm{eff}}\)；
- 不允许全部 Case 统一错误地使用 \(11/15\)；
- filler 虽参与编码和发送，但不属于有效 payload；
- 公平比较时使用净荷有效码率。

---

# 六、指标定义

## 6.1 BER

只统计原始有效 payload：

\[
\mathrm{BER}=
\frac{\text{错误 payload bit 总数}}
{\text{发送 payload bit 总数}}
\]

不统计：

```text id="uai6wy"
filler
缩短补回位
母码虚拟位
校验位
```

## 6.2 FER

一帧 200 bit 或 300 bit payload 中，只要存在至少 1 bit 错误：

```text id="9ftxaj"
frameError = 1
```

\[
\mathrm{FER}=
\frac{N_{\mathrm{frameError}}}
{N_{\mathrm{frames}}}
\]

对于分块 BCH：

> 19 个或 28 个 BCH 小块中，只要任何一个小块最终恢复错误，完整电文就计为一个误帧。

## 6.3 译码成功率

不能简单只写成 \(1-\mathrm{FER}\)，建议同时保存两个口径：

### 真实成功率

\[
P_{\mathrm{trueSuccess}}=
\frac{\text{payload 完全正确帧数}}
{\text{总帧数}}
\]

### 译码器报告成功率

\[
P_{\mathrm{reportedSuccess}}=
\frac{\text{译码器未报告失败帧数}}
{\text{总帧数}}
\]

两者差异可以揭示：

```text id="wi9jvu"
误纠
未检测错误
错误状态判定不准确
```

## 6.4 误纠率

特别是 BCH(15,11,1) 双错情况下：

\[
P_{\mathrm{miscorrection}}=
\frac{\text{错误输入被译成另一合法码字的次数}}
{\text{双错及超纠错能力测试总数}}
\]

## 6.5 编码增益

历史文本中的公式排版出现了错误，正确形式是：

\[
G_{\mathrm{coding}}
=
\left(\frac{E_b}{N_0}\right)_{\mathrm{reference}}
-
\left(\frac{E_b}{N_0}\right)_{\mathrm{candidate}}
\]

主比较点：

```text id="u0wzbh"
FER = 10^-2
```

建议输出：

1. 分块 BCH 相对未编码 BPSK 的编码增益；
2. 整块 BCH 相对未编码 BPSK 的编码增益；
3. 整块 BCH 相对同 payload 长度分块 BCH 的水平差。

曲线未覆盖目标 FER 时：

```text id="vul3ol"
N/A
```

只能在相邻仿真点之间进行对数域线性插值，禁止远距离外推。

---

# 七、工程目录

```text id="r76k7s"
Task/BCH/
├─ segmented/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ stages/
│  ├─ scripts/
│  ├─ build/
│  ├─ results/
│  ├─ matlab/
│  ├─ config/
│  └─ docs/
│
├─ block/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ stages/
│  ├─ scripts/
│  ├─ build/
│  ├─ results/
│  ├─ matlab/
│  ├─ config/
│  └─ docs/
│
├─ shared/
│  ├─ include/
│  ├─ src/
│  └─ tests/
│
├─ comparison/
│  ├─ scripts/
│  ├─ results/
│  └─ docs/
│
├─ AGENTS.md
└─ README.md
```

`comparison` 只用于：

```text id="b63k2y"
分块与整块曲线汇总
编码增益计算
复杂度对比
最终推荐表
```

它不存放核心编译码实现。

---

# 八、BCH 完整 Stage 路线

下面建议使用**全项目连续编号**。假设公共基础设施已经完成或独立推进，BCH 从 Stage04 开始。

---

## Phase A：BCH(15,11,1) 定义与实现

## Stage04：BCH(15,11,1) 参数和位序冻结

### 目标

冻结：

- \(n=15,k=11,t=1\)；
- \(g(x)=x^4+x+1\)；
- 信息位与校验位的排列；
- MSB/LSB 多项式映射；
- 系统码拼接方式；
- syndrome 定义；
- 错误位置编号；
- 200/300 bit 分组规则；
- filler 添加和删除规则。

### 必须明确的位序示例

建议统一规定：

```text id="nt7lyr"
数组下标 0 对应多项式最高次项
message[0] ↔ x^10
message[10] ↔ x^0

codeword[0] ↔ x^14
codeword[14] ↔ x^0

系统码格式：
[11 bit message][4 bit parity]
```

但这个规定必须用 MATLAB 参考向量验证后才能冻结。

### 输出文件

```text id="y4a8aw"
Task/BCH/segmented/docs/bch15_definition.md
Task/BCH/segmented/docs/bch15_bit_order.md
Task/BCH/segmented/config/bch15_frozen_config.csv
Task/BCH/segmented/config/bch15_test_vectors.csv
```

### 测试向量至少包含

```text id="gvdi3q"
全零
全一
仅最高信息位为 1
仅最低信息位为 1
交替 101010...
交替 010101...
固定随机向量 10 组
```

### Gate

```text id="8zcni2"
PASS_STAGE04_BCH15_DEFINITION
```

### 停止边界

不实现正式编码器、译码器、AWGN。

---

## Stage05：BCH(15,11,1) 单块编码器

### 输入输出

```text id="b7fux2"
输入：11 bit
输出：15 bit
```

### 算法

\[
c(x)=x^4m(x)+r(x)
\]

\[
r(x)=x^4m(x)\bmod g(x)
\]

### 建议模块

```text id="8iqgrj"
bch15_types.h
bch15_polynomial.h/.cpp
bch15_encoder.h/.cpp
test_bch15_encoder.cpp
```

### 测试

1. 固定测试向量；
2. 全部 \(2^{11}=2048\) 个输入；
3. 每个码字验证：

\[
c(x)\bmod g(x)=0
\]

4. 验证系统位未改变；
5. 验证码字无重复；
6. 导出全部 2048 条：

```text id="a45lwf"
input_decimal
input_bits
parity_bits
codeword_bits
remainder
valid_codeword
```

### Gate

```text id="051q4w"
PASS_STAGE05_BCH15_ENCODER
```

---

## Stage06：BCH(15,11,1) syndrome 表

### 目标

单独建立并验证：

```text id="s5r9wd"
15 个单比特错误位置
→ 15 个非零 syndrome
```

### 检查

- syndrome 0 只对应无错；
- 15 个单错 syndrome 必须非零；
- 15 个单错 syndrome 必须互不相同；
- syndrome 表不能存在重复 key；
- syndrome 与错误位置编号一致。

### 输出

```text id="tmy1u2"
syndrome_table.csv
syndrome_definition.md
test_syndrome_table.cpp
```

### Gate

```text id="wf6wgn"
PASS_STAGE06_BCH15_SYNDROME_TABLE
```

---

## Stage07：BCH(15,11,1) 查表译码器

### 流程

```text id="7wf42w"
接收 15 bit
    ↓
计算 syndrome
    ↓
syndrome=0？
 ├─ 是：直接输出
 └─ 否：查 syndrome 表
             ↓
         翻转对应 bit
             ↓
         再算 syndrome
             ↓
         提取 11 bit 信息
```

### 译码结果结构

```cpp id="ywimlw"
struct Bch15DecodeResult {
    std::array<uint8_t, 11> message;
    std::array<uint8_t, 15> correctedCodeword;
    uint8_t syndromeBefore;
    uint8_t syndromeAfter;
    int correctedPosition;
    DecodeStatus status;
};
```

### 状态建议

```text id="qrsnhg"
NO_ERROR
CORRECTED_SINGLE_ERROR
POST_CHECK_FAILED
UNRECOGNIZED_SYNDROME
```

不建议让译码器直接把双错统一标记为 `UNCORRECTABLE`，因为对于完备汉明码性质的 BCH(15,11,1)，部分多错模式可能产生与某个单错相同的 syndrome，进而发生误纠。真实分类必须通过与原始码字对比完成。

### 穷举测试

无错：

\[
2048
\]

单错：

\[
2048\times15=30720
\]

要求：

```text id="fgay8m"
无错 payload mismatch = 0
单错 payload mismatch = 0
单错定位 mismatch = 0
post syndrome mismatch = 0
```

### Gate

```text id="pjefi7"
PASS_STAGE07_BCH15_DECODER
```

---

## Stage08：双错与多错误纠审计

这是原计划中应该单独拆出的一个重要 Stage。

### 双错全集

每个码字双错组合：

\[
\binom{15}{2}=105
\]

总测试量：

\[
2048\times105=215040
\]

### 建议统计

```text id="40envu"
totalPatterns
decodedToOriginal
detectedFailure
miscorrectedToAnotherCodeword
postCheckPassedButPayloadWrong
statusDistribution
```

还可抽样测试：

```text id="g81dg6"
3 bit 错误
4 bit 错误
随机高权重错误
```

### 目的

明确回答：

- 双错是否能检测；
- 双错误纠比例；
- post syndrome 为 0 是否等价于 payload 正确；
- 译码状态能否真实反映结果。

### Gate

这里不要求双错都能检测，只要求审计完整、结果可解释：

```text id="9ce690"
PASS_STAGE08_BCH15_MISCORRECTION_AUDIT
```

---

## Stage09：200/300 bit 分块适配器

### 模块

```text id="ez3yby"
segmentPayload()
appendFiller()
encodeSegmentedFrame()
decodeSegmentedFrame()
removeFiller()
```

### 需要保存的帧元数据

```text id="qaaldy"
payloadLength
segmentCount
fillerLength
encodedLength
segmentIndex
originalFrameIndex
```

### 测试

- 200 bit → 19 组 → 285 bit；
- 300 bit → 28 组 → 420 bit；
- 最后一组 filler 全为 0；
- 编码后逐组均为合法 BCH 码字；
- 无噪声译码后恢复原 payload；
- filler 不计入 BER；
- filler 错误不应直接计入 payload BER；
- 任一 payload bit 错误导致 frame error。

### Gate

```text id="gf1gm3"
PASS_STAGE09_BCH_SEGMENT_ADAPTER
```

---

## Stage10：MATLAB 独立参考验证

### 对比内容

1. 生成多项式；
2. 2048 个输入对应码字；
3. syndrome；
4. 15 个单错位置；
5. 单块解码信息；
6. 200 bit 完整帧；
7. 300 bit 完整帧。

### 推荐范围

```text id="hh889e"
全部 2048 个单块输入
全部 30720 个单错测试
固定 100 帧 200 bit
固定 100 帧 300 bit
```

### 必须输出

```text id="rat36b"
encodedMismatchCount
syndromeMismatchCount
correctedPositionMismatchCount
decodedPayloadMismatchCount
frameAdapterMismatchCount
```

全部必须为 0。

### 注意

MATLAB 和 C++ 必须使用完全相同的：

```text id="6t6tzz"
位序
多项式表示
系统码排列
filler 位置
错误位置编号
```

### Gate

```text id="5ay5j7"
PASS_STAGE10_BCH15_MATLAB_REFERENCE
```

---

## Stage11：无噪声与人工扰动验证

### 无噪声链路

```text id="k004ai"
payload
→ 分块
→ BCH 编码
→ BPSK
→ y=x
→ 硬判决
→ BCH 译码
→ 去 filler
```

要求：

```text id="5723hv"
BER = 0
FER = 0
payloadMismatch = 0
```

### 人工扰动

每帧人为指定：

```text id="sxolue"
0 个错误
每个 BCH 小块 1 个错误
单个小块 1 个错误
单个小块 2 个错误
跨多个小块各 1 个错误
```

这个 Stage 是正式 AWGN 前的最后逻辑 Gate。

### Gate

```text id="q72tnr"
PASS_STAGE11_BCH_SEGMENTED_NOISELESS
```

---

# 九、分块 BCH AWGN 实验

## Stage12：AWGN smoke

### 建议 SNR 点

首次可用：

```text id="7mnsc8"
Eb/N0 = 0, 2, 4, 6 dB
```

这只是工程链路检查，不是最终固定范围。

### 停止规则

```text id="ehfse3"
minFrames = 20
targetFrameErrors = 5
maxFrames = 100
```

### 检查内容

- 两个 payload Case 都能运行；
- BER、FER 大体随 SNR 降低；
- 低 SNR 有足够错误；
- 高 SNR 不出现异常；
- sigma 与有效码率正确；
- CSV 字段完整；
- 图为对数纵轴；
- 无 NaN/Inf；
- seed、frameIndex 和 stopReason 正确保存。

### Gate

```text id="fmd6nn"
PASS_STAGE12_BCH_SEGMENTED_SMOKE
```

---

## Stage13：AWGN prescan

### 初始建议

```text id="t9enev"
Eb/N0 = 0.0:0.5:8.0 dB
```

具体范围由 smoke 调整。

### 停止规则

```text id="f8egd0"
minFrames = 300
targetFrameErrors = 30
maxFrames = 2000
```

### 目标

确定：

- FER 从约 \(10^{-1}\) 到 \(10^{-3}\) 的范围；
- 200/300 bit waterfall；
- 高 SNR 是否跑满；
- 单点运行时间；
- formal 需要哪些 SNR 点；
- 是否需要扩大帧池。

### 输出

```text id="jcs3z5"
prescan_summary.csv
recommended_formal_grid.csv
runtime_estimate.csv
ber_prescan.png
fer_prescan.png
```

### Gate

```text id="6y1bos"
PASS_STAGE13_BCH_SEGMENTED_PRESCAN
```

---

## Stage14：formal trial

选择三个点：

```text id="ps8skr"
低 SNR 点
waterfall 中心点
高 SNR 点
```

### 参数

```text id="f2c222"
minFrames = 5000
targetFrameErrors = 100
maxFrames = 20000
```

### 检查

- 停止逻辑；
- checkpoint/resume；
- 运行时间；
- frame pool 索引；
- 相同 seed 重跑一致；
- 高 SNR 0 error 点的统计表达；
- 正式结果文件是否完整。

### Gate

```text id="apcgv9"
PASS_STAGE14_BCH_SEGMENTED_FORMAL_TRIAL
```

---

## Stage15：分块 BCH AWGN formal

### 参数原则

```text id="qg5mgw"
SNR 步长：0.1 或 0.2 dB
minFrames：5000
targetFrameErrors：200
maxFrames：50000
```

停止条件：

\[
\left(
N_{\mathrm{frames}}\ge N_{\min}
\land
N_{\mathrm{FE}}\ge N_{\mathrm{FE,target}}
\right)
\lor
N_{\mathrm{frames}}=N_{\max}
\]

### 正式输出

- BER；
- FER；
- 真实成功率；
- 报告成功率；
- 误纠率；
- 实际帧数；
- bit error 数；
- frame error 数；
- 停止原因；
- 平均/最大编码时间；
- 平均/P95/P99/最大译码时间；
- 每帧平均小块错误数；
- 每帧平均纠正小块数。

### Gate

```text id="2rrfwz"
PASS_STAGE15_BCH_SEGMENTED_FORMAL
```

---

# 十、整块缩短 BCH 路线

## Stage16：整块 BCH 参数冻结

必须分别确认：

### 200 bit Case

```text id="vep4jt"
母码 n0
母码 k0
纠错能力 t
缩短位数 s
缩短后 n
缩短后 k
primitive polynomial
generator polynomial
MATLAB 参数
```

理论上若从 \((255,207)\) 缩短到 \(k=200\)：

\[
s=207-200=7
\]

\[
n=255-7=248
\]

### 300 bit Case

若从 \((511,421)\) 缩短到 \(k=300\)：

\[
s=421-300=121
\]

\[
n=511-121=390
\]

这些长度关系是成立的，但仍需验证母码本身是否合法且与 MATLAB 定义一致。

### Gate

```text id="bs1s6b"
PASS_STAGE16_BCH_BLOCK_PARAMETER_FREEZE
```

---

## Stage17：GF\((2^m)\) 基础运算

实现：

```text id="iw1j8i"
GF 加法
GF 乘法
GF 除法
GF 逆元
指数表
对数表
多项式求值
```

分别针对可能需要的：

```text id="ukb8b2"
GF(2^8)
GF(2^9)
```

测试：

- \(a+0=a\)；
- \(a+a=0\)；
- \(a\times1=a\)；
- \(a\times a^{-1}=1\)；
- log/antilog 互逆；
- MATLAB 随机对比；
- 全域或抽样闭合检查。

### Gate

```text id="3hjril"
PASS_STAGE17_BCH_GF_ARITHMETIC
```

---

## Stage18：整块母码与缩短编码器

### 缩短编码流程

```text id="djburt"
200/300 bit payload
        ↓
在冻结位置补 s 个已知 0
        ↓
形成母码信息向量
        ↓
母 BCH 系统编码
        ↓
删除对应的 s 个已知系统位
        ↓
输出 248/390 bit 缩短码字
```

### 测试

- 固定向量；
- 随机帧；
- 母码合法性；
- 缩短位置一致；
- 系统位恢复；
- MATLAB 逐帧对比。

### Gate

```text id="dgsju5"
PASS_STAGE18_BCH_BLOCK_ENCODER
```

---

## Stage19：BM 错误位置多项式

实现：

```text id="472twm"
syndrome 序列
→ Berlekamp-Massey
→ 错误位置多项式 Λ(x)
```

独立测试：

- 无错；
- 1 错；
- 2 错；
- \(t\) 错；
- 超过 \(t\)；
- 与 MATLAB 中间结果对比。

### Gate

```text id="e8zy7f"
PASS_STAGE19_BCH_BM
```

---

## Stage20：Chien 搜索与完整译码器

流程：

```text id="kzf93w"
缩短码接收
→ 补回已知 0
→ 计算 syndrome
→ BM
→ Chien 搜索
→ 翻转错误位
→ 重新计算 syndrome
→ 删除补回位
→ 提取 payload
```

测试错误重量：

```text id="lqpz0k"
0
1
2
...
t
t+1
随机超过 t
```

要求：

```text id="c5auwm"
≤t 错误全部恢复
超过 t 的行为完整审计
```

### Gate

```text id="2sqqi1"
PASS_STAGE20_BCH_BLOCK_DECODER
```

---

## Stage21：整块 BCH MATLAB 独立参考

对比：

- 生成多项式；
- 缩短前母码；
- 缩短后码字；
- syndrome；
- BM 多项式；
- Chien 错误位置；
- 解码 payload；
- 随机 200/300 bit 帧；
- 从 0 到 \(t\) 的错误注入。

### Gate

```text id="afy4lk"
PASS_STAGE21_BCH_BLOCK_MATLAB_REFERENCE
```

---

## Stage22：整块无噪声与扰动验证

要求：

```text id="u5x8py"
200 bit noiseless BER/FER = 0
300 bit noiseless BER/FER = 0
≤t 错误恢复率 = 100%
```

### Gate

```text id="hzi115"
PASS_STAGE22_BCH_BLOCK_NOISELESS
```

---

## Stage23～Stage26：整块 AWGN

```text id="ao0e7a"
Stage23：smoke
Stage24：prescan
Stage25：formal trial
Stage26：formal
```

参数口径与分块方案一致，但使用各自：

```text id="y6a487"
Ntx
Reff
编码/译码器
时延统计
```

---

# 十一、分块与整块 BCH 综合对比

## Stage27：AWGN 综合比较

同一 payload 长度分别比较：

```text id="8egrpk"
BCH-S200 vs BCH-B200
BCH-S300 vs BCH-B300
```

### 必须分别画图

1. 200 bit BER；
2. 200 bit FER；
3. 300 bit BER；
4. 300 bit FER；
5. 平均译码时延；
6. 最大译码时延；
7. 编码增益；
8. 发送长度与有效码率。

不建议把 200 bit 和 300 bit 的所有曲线全部挤在一张图中。

### 对比表

| 指标 | 分块 200 | 整块 200 | 分块 300 | 整块 300 |
|---|---:|---:|---:|---:|
| 发送长度 | 285 | 248 | 420 | 390 |
| 有效码率 | 0.702 | 0.806 | 0.714 | 0.769 |
| 纠错组织 | 19 个单错码 | 整块 \(t\) 错 | 28 个单错码 | 整块 \(t\) 错 |
| 平均译码时延 |  |  |  |  |
| 最大译码时延 |  |  |  |  |
| FER@指定 SNR |  |  |  |  |
| 编码增益 |  |  |  |  |
| 误纠率 |  |  |  |  |

### Gate

```text id="ocjjj7"
PASS_STAGE27_BCH_AWGN_COMPARISON
```

---

# 十二、复杂信道和交织

老师文档将交织明确设为独立测试项，并要求比较无交织、块交织、行列交织和伪随机交织对突发错误的改善。fileciteturn2file8

不应一开始就把所有复杂信道全组合运行。应先从 AWGN formal 中选出：

```text id="k320r6"
一个 200 bit 分块方案
一个 200 bit 整块方案
一个 300 bit 分块方案
一个 300 bit 整块方案
```

---

## Stage28：突发错误模型冻结

建议至少实现两种模式。

### 模式 A：硬比特连续翻转

```text id="90i3vt"
在发送或硬判决后
随机选择起点
连续翻转 L_burst 个 bit
```

### 模式 B：符号段强干扰或擦除

```text id="1ov3d5"
对连续 L_burst 个符号：
y = 0
或
y = x + σ_burst z
```

建议突发长度：

```text id="p766te"
L_burst ∈ {1, 2, 4, 8, 12, 16, 24, 32}
```

### Gate

```text id="db2fz9"
PASS_STAGE28_BURST_CHANNEL_DEFINITION
```

---

## Stage29：交织器互逆验证

实现：

```text id="trtg0h"
无交织
行列块交织
矩阵转置式交织
固定 seed 伪随机交织
```

每种交织器必须验证：

\[
\Pi^{-1}(\Pi(x))=x
\]

同时记录：

```text id="cavw6t"
interleaverType
interleaverLength
rows
columns
seed
bufferDepth
```

### Gate

```text id="cnjklg"
PASS_STAGE29_BCH_INTERLEAVER
```

---

## Stage30：BCH 突发错误与交织实验

实验矩阵建议：

```text id="1hulnm"
Payload：200、300
编码：分块、整块
交织：无、行列、块、伪随机
突发长度：1、2、4、8、16、32
信道强度：2～3 个代表点
```

### 输出

\[
\Delta\mathrm{FER}
=
\mathrm{FER}_{\mathrm{noInterleaver}}
-
\mathrm{FER}_{\mathrm{interleaver}}
\]

还应报告：

```text id="ufmage"
相对 FER 改善比例
成功率改善
交织缓存长度
额外内存
交织/去交织运行时间
预计缓存时延
```

### 重点观察

对于分块 BCH：

- 交织前，一个长突发可能集中破坏一个或少数 BCH 小块；
- 若某小块出现 2 个以上错误，可能误纠；
- 交织后，突发错误被分散到多个小块；
- 当每个小块最多约 1 个错误时，BCH(15,11,1) 可以逐块纠正。

但交织深度不足时，也可能只是把错误重新排列，无法使每块错误数降到 1 以下。

### Gate

```text id="chxzcv"
PASS_STAGE30_BCH_BURST_INTERLEAVING
```

---

## Stage31～Stage34：代表性复杂信道

建议顺序：

```text id="c4vlwa"
Stage31：短时遮挡
Stage32：多径衰落
Stage33：频偏/信道突变
Stage34：BCH 复杂信道综合比较
```

每个信道都必须先冻结：

```text id="sj03k4"
模型公式
参数
随机 seed
接收端是否均衡
起点与持续长度
输出指标
```

避免只写“测试多径”却没有可复现参数。

---

# 十三、时延测试计划

## 13.1 测量内容

每个 Case 至少统计：

```text id="o0s5zd"
avgEncodeTime_us
p95EncodeTime_us
maxEncodeTime_us
avgDecodeTime_us
p95DecodeTime_us
p99DecodeTime_us
maxDecodeTime_us
```

分块 BCH 还要统计：

```text id="y8coy6"
avgDecodeTimePerBlock_us
maxDecodeTimePerBlock_us
avgBlocksCorrectedPerFrame
```

## 13.2 测试条件

- Release 编译；
- 固定编译器和优化选项；
- 固定 CPU；
- 单线程；
- 预热后开始统计；
- 不把磁盘写入、CSV、绘图时间计入核心译码时延；
- 同一 Case 重复多轮；
- 记录机器和编译环境。

## 13.3 分块 BCH 的时延应报告两种口径

### 串行整帧时延

19 或 28 个小块顺序译码总时长。

### 理论并行小块时延

若未来硬件可并行处理多个小块，可报告单块最大译码时延作为并行实现参考，但必须明确这是理论工程分析，不能与当前单线程 C++ 时间混为一谈。

---

# 十四、复杂度分析

## 14.1 BCH(15,11,1)

理论操作：

```text id="sv51o7"
每块一次固定长度多项式除法
一次 syndrome
最多一次 15 项查表
最多一次 bit 翻转
```

存储：

```text id="m9mh67"
15 个 syndrome→位置映射
```

一帧复杂度近似与块数线性相关：

\[
O(B)
\]

其中：

```text id="17p3se"
B=19 或 28
```

## 14.2 整块 BCH

主要模块：

```text id="rflj7z"
2t 个 syndrome 计算
Berlekamp-Massey
Chien 搜索
GF 对数/指数表
```

理论复杂度可按：

```text id="7wb629"
syndrome：O(nt)
BM：O(t²)
Chien：O(nt)
```

同时报告：

- GF 表大小；
- syndrome 数；
- BM 迭代次数；
- Chien 检查位置数；
- 每帧 GF 加法、乘法和除法估计量。

---

# 十五、结果文件统一规范

每个正式 Case：

```text id="6v69td"
results/stageXX_case_name/
├─ config_used.csv
├─ frozen_case.json
├─ snr_summary.csv
├─ runtime_summary.csv
├─ decoder_status_summary.csv
├─ miscorrection_summary.csv
├─ frame_detail_sample.csv
├─ ber.png
├─ fer.png
├─ success_rate.png
├─ runtime.png
├─ run_log.txt
├─ checkpoint/
├─ gate_report.md
├─ result_manifest.json
└─ completion.flag
```

`snr_summary.csv` 建议字段：

```text id="5ubanf"
caseId
payloadLength
codeFamily
organization
motherN
motherK
t
segmentCount
fillerLength
txLength
effectiveRate
EbN0_dB
sigma
frames
frameErrors
bitErrors
BER
FER
trueSuccessRate
reportedSuccessRate
miscorrectionFrames
avgEncodeTime_us
avgDecodeTime_us
p95DecodeTime_us
p99DecodeTime_us
maxDecodeTime_us
stopReason
masterSeed
firstFrameIndex
lastFrameIndex
gitCommit
```

---

# 十六、每个 Stage 的审计文件

根据现有 Git 工作流，每个 Stage 只完成一个明确任务，从干净 `main` 创建独立分支，测试和审查后才允许合并。fileciteturn3file1

每个 Stage 目录必须包含：

```text id="xwtxap"
stage_plan.md
changed_files.md
validation_report.md
manifest.json
changes.patch
frozen_config.csv
commands_used.md
git_commit.txt
known_issues.md
snapshot/
```

`changed_files.md` 必须写清：

- 相对路径；
- 新增、修改或删除；
- 文件用途；
- 修改原因；
- 关键函数；
- 关键代码块；
- 是否影响旧行为；
- 与当前 Stage 的关系。

Git 分支示例：

```text id="9ucq7v"
stage04-bch15-definition
stage05-bch15-encoder
stage06-bch15-syndrome-table
stage07-bch15-decoder
stage08-bch15-miscorrection-audit
```

Codex 默认停止在：

```text id="vgij27"
修改
→ 编译
→ 测试
→ 审计文件
→ 按授权 commit/push 当前 Stage 分支
→ 停止
```

不得自动 merge `main`。

---

# 十七、完整执行顺序

```text id="31dqad"
Stage04  参数与位序冻结
   ↓
Stage05  BCH(15,11,1) 编码器
   ↓
Stage06  syndrome 表
   ↓
Stage07  查表译码器
   ↓
Stage08  双错与误纠审计
   ↓
Stage09  200/300 bit 分块适配
   ↓
Stage10  MATLAB 独立参考
   ↓
Stage11  无噪声与人工扰动
   ↓
Stage12  AWGN smoke
   ↓
Stage13  AWGN prescan
   ↓
Stage14  formal trial
   ↓
Stage15  分块 BCH formal
   ↓
Stage16  整块 BCH 参数冻结
   ↓
Stage17  GF 运算
   ↓
Stage18  整块编码器
   ↓
Stage19  BM
   ↓
Stage20  Chien 与完整译码器
   ↓
Stage21  MATLAB 参考
   ↓
Stage22  无噪声与纠错能力验证
   ↓
Stage23  整块 smoke
   ↓
Stage24  整块 prescan
   ↓
Stage25  整块 formal trial
   ↓
Stage26  整块 formal
   ↓
Stage27  分块/整块 AWGN 对比
   ↓
Stage28  突发错误模型
   ↓
Stage29  交织器
   ↓
Stage30  交织抗突发错误
   ↓
Stage31～34  代表性复杂信道
   ↓
Stage35  BCH 最终综合报告
```

---

# 十八、现在最合理的第一轮任务

当前不要直接实现完整 BCH、AWGN 和整块 BM 译码器。

第一轮严格只完成：

```text id="z20omz"
Stage04：BCH(15,11,1) 参数、位序和测试向量冻结
```

审查通过后再完成：

```text id="7bme9p"
Stage05：BCH(15,11,1) 单块编码器
```

第一轮结束点建议是：

```text id="qwcwbq"
PASS_STAGE05_BCH15_ENCODER
```

这时你能够人工检查：

- 11 bit 输入；
- 多项式映射；
- 4 bit 余式；
- 15 bit 系统码；
- 全部 2048 个码字；
- \(c(x)\bmod g(x)=0\)；
- MATLAB 固定向量是否一致。

这样后续 syndrome 表和译码器建立在已经冻结、可信的位序之上，不会出现“编码器和译码器自己互相匹配，但与 MATLAB 或标准定义完全不同”的问题。
