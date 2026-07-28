



# 卷积码 CC 整体实验初步规划与设计

我已经结合你上传的老师任务附件、项目参数规划、公共基础仿真规划、窗口交接信息和 Git 工作流要求进行了统一检查。

老师对卷积码的定位非常明确：

> 卷积码面向约 300 bit 的高速电文，是后续与 5G NR LDPC 比较时的工程基线方案。重点研究硬/软判决 Viterbi、1/2 与打孔码率、整块零尾编码、连续编码、按时隙分块和滑窗译码。

老师附件还明确规定：

- 高速电文只保留约 300 bit；
- 卷积码参数采用 \(K=7\)、母码率 \(1/2\)、生成多项式 \(171_{\mathrm{oct}}\) 和 \(133_{\mathrm{oct}}\)；
- 通过打孔支持 \(2/3\)、\(3/4\)；
- 整块编码使用尾比特清零；
- 按时隙分块时采用连续编码和滑窗译码；
- 要统计滑窗长度、回溯深度、BER、FER、时延和复杂度。fileciteturn0file2L1-L20

现有公共规划也已经冻结了实际码率、随机帧、每帧独立噪声、公平对比、BER/FER、停止规则和绘图审计要求。fileciteturn0file7L1-L20

---

# 一、先明确 CC、LDPC 对应哪个场景

老师的场景划分应当严格使用：

| 场景 | 对应内容 |
|---|---|
| S3 | 高速卷积码的码率、整块、分块、滑窗和译码设计 |
| S4 | 高速 LDPC 的短码长适配 |
| S5 | 卷积码与 LDPC 在不同信道下的比较 |
| S6 | 不同译码算法的比较 |
| S7 | BCH、卷积码的交织抗突发错误测试 |

因此，本轮卷积码的独立建设阶段全部放到：

```text
Task/CC/simulation/stages/S3/
```

同步开始的 LDPC 独立建设阶段放到：

```text
Task/LDPC/simulation/stages/S4/
```

不要出现：

```text
Task/CC/simulation/stages/S4/
```

因为 S4 在老师的任务定义中是 LDPC，不是卷积码。

后续当 CC 和 LDPC 各自的 AWGN 基线都完成后，再建立跨编码实验：

```text
Task/Comparison/simulation/stages/S5/
```

或者按照当前仓库实际结构，在 CC/LDPC 之外建立统一的对比入口。S5 不应在现在提前混入 S3 或 S4。

---

# 二、卷积码的基本定位

卷积码这一轮不是简单地“实现一个 Viterbi 译码器”，而是要回答四类工程问题。

## 2.1 纠错性能

比较：

- 硬判决 Viterbi；
- 浮点软判决 Viterbi；
- 后续量化软判决 Viterbi；
- 码率 \(1/2\)、\(2/3\)、\(3/4\)。

主要指标：

```text
BER
FER
编码增益
达到目标 FER 所需的 SNR
```

## 2.2 传输效率

比较：

- 实际发送码长；
- 实际码率；
- 有效吞吐；
- 尾比特开销；
- 打孔带来的吞吐提升和性能损失。

## 2.3 实时处理能力

比较：

- 300 bit 整块零尾；
- 连续编码；
- 按时隙划分；
- 滑窗 Viterbi；
- 回溯深度；
- 首比特输出时延；
- 稳态吞吐。

## 2.4 工程复杂度

比较：

- 64 状态 ACS 运算量；
- 幸存路径内存；
- 硬判决和软判决复杂度；
- 滑窗缓存长度；
- 浮点与量化软信息开销；
- 平均、P95、最大译码时延。

卷积码作为工程基线的价值，不一定体现为 BER 最低，而更可能体现为：

- 结构成熟；
- 译码流程稳定；
- 可连续输出；
- 时延比较确定；
- 容易流水线化；
- 不必等待整个大块全部接收完成后才工作。

这一定位与现有任务分析文件一致。fileciteturn0file5L1-L20

---

# 三、建议的 CC 目录结构

根据你的要求，CC 专用代码、脚本、编译目录和结果必须全部位于 `Task/CC` 内。

建议使用：

```text
Task/CC/
├─ shared/
│  ├─ include/
│  ├─ src/
│  ├─ tests/
│  ├─ config/
│  └─ docs/
│
├─ block/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ scripts/
│  ├─ build/
│  ├─ matlab/
│  ├─ config/
│  ├─ docs/
│  └─ results/
│
├─ continuous/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ scripts/
│  ├─ build/
│  ├─ matlab/
│  ├─ config/
│  ├─ docs/
│  └─ results/
│
├─ simulation/
│  └─ stages/
│     └─ S3/
│
└─ README.md
```

其中：

### `shared/`

只放卷积码内部共享模块：

```text
trellis 定义
状态转移表
171/133 生成多项式
打孔图样
去打孔
路径度量公共类型
ACS 基础结构
幸存路径结构
统一 tie-breaking 规则
```

不要把这些 CC 专用内容放入 `Task/Common`。

### `block/`

保存：

```text
300 bit 整块零尾编码
整块硬判决 Viterbi
整块软判决 Viterbi
1/2、2/3、3/4 打孔方案
整块时延与性能实验
```

### `continuous/`

保存：

```text
跨时隙保持编码器状态
连续卷积编码
滑窗 Viterbi
窗口移动
逐步输出
边界处理
连续流缓存
```

老师原始要求确实同时要求整块和按时隙分块、连续编码与滑窗译码。fileciteturn0file11L40-L58

---

# 四、每个实验 Stage 的目录和命名

每个实验阶段放在：

```text
Task/CC/simulation/stages/S3/stageXX_name/
```

例如：

```text
Task/CC/simulation/stages/S3/stage01_cc_contract/
Task/CC/simulation/stages/S3/stage02_trellis_encoder/
Task/CC/simulation/stages/S3/stage03_hard_viterbi/
```

建议每个阶段包含：

```text
stageXX_name/
├─ include/
├─ src/
├─ tests/
├─ scripts/
├─ config/
├─ matlab/
├─ results/
├─ stage_plan.md
├─ changed_files.md
├─ validation_report.md
├─ frozen_config.csv
├─ manifest.json
├─ commands_used.md
├─ changes.patch
├─ git_commit.txt
└─ known_issues.md
```

结果只进入该阶段的：

```text
stageXX_name/results/
```

例如：

```text
stage09_awgn_formal/results/
├─ stage09_awgn_formal_point_results.csv
├─ stage09_awgn_formal_curve_summary.csv
├─ stage09_awgn_formal_k300_r12_hard_ber.png
├─ stage09_awgn_formal_k300_r12_hard_fer.png
├─ stage09_awgn_formal_k300_r12_soft_ber.png
├─ stage09_awgn_formal_k300_r12_soft_fer.png
├─ stage09_awgn_formal_figure_data.csv
├─ stage09_awgn_formal_plot_manifest.json
└─ stage09_awgn_formal_plot_check.md
```

不允许：

```text
result.csv
figure1.png
plot.png
test.csv
output.png
```

Git 仍应遵循“一阶段一分支、测试通过后 commit/push、不自动合并 main”的规则。fileciteturn0file4L1-L20

---

# 五、卷积码基础参数冻结建议

## 5.1 主场景

```text
payloadLength = 300 bit
constraintLength = 7
memory = 6
stateCount = 64
motherRate = 1/2
generator1 = 171 oct
generator2 = 133 oct
initialState = 0
modulation = BPSK
baselineChannel = AWGN
```

200 bit 只做：

```text
接口兼容测试
边界长度测试
非正式扩展测试
```

不做 CC 正式主曲线。

## 5.2 整块零尾

300 bit payload 后加入：

\[
K-1=6
\]

个零尾比特，使编码器回到全零状态。

因此：

\[
K_{\text{payload}}=300
\]

\[
K_{\text{codec input}}=300+6=306
\]

母码 \(1/2\) 输出：

\[
N_{\text{mother}}=2\times306=612
\]

实际码率统一按：

\[
R_{\text{actual}}
=
\frac{K_{\text{payload}}}
{N_{\text{transmitted}}}
\]

所以：

\[
R_{\text{actual},1/2}
=
\frac{300}{612}
\approx0.490196
\]

不能直接把这个 Case 写成实际码率 \(0.5\)。

老师文件中的“约 612 bit”也正是包含了 6 个尾比特后的结果。fileciteturn0file26L1-L20

## 5.3 打孔码率

正式目标：

```text
1/2
2/3
3/4
```

目前老师附件只规定了目标码率，没有给出唯一的打孔矩阵。因此打孔图样不能直接凭习惯写死，必须经过专门 Stage 冻结。

候选示意可以是：

### \(2/3\) 候选

```text
输出时刻：       t0   t1
第一路输出保留：  1    1
第二路输出保留：  1    0
```

每 2 个输入 bit 产生 4 个母码 bit，发送 3 个。

### \(3/4\) 候选

```text
输出时刻：       t0   t1   t2
第一路输出保留：  1    1    0
第二路输出保留：  1    0    1
```

每 3 个输入 bit 产生 6 个母码 bit，发送 4 个。

但这只是候选表示，不应直接视为最终冻结方案。

正式冻结时必须明确：

- 图样周期；
- 两路输出排列顺序；
- 图样从哪个输出 bit 开始；
- 尾比特区域是否继续按相同周期打孔；
- 周期末尾不足时怎么处理；
- 实际发送 bit 数；
- 实际码率；
- C++ 和 MATLAB 是否一致；
- 软去打孔如何填充中性信息；
- 硬译码如何避免把缺失位误认为真实 0 或 1。

---

# 六、硬判决和软判决 Viterbi 的设计

## 6.1 硬判决 Viterbi

接收符号先转换为：

```text
y >= 0 → 0
y < 0  → 1
```

分支度量采用汉明距离：

\[
M_{\text{hard}}
=
\sum_i
\mathbf 1(r_i\ne c_i)
\]

其中：

- \(r_i\)：接收硬比特；
- \(c_i\)：某条 trellis 分支应输出的编码 bit。

优点：

- 实现简单；
- 度量是整数；
- 复杂度较低；
- 容易硬件实现。

缺点：

- 丢失接收可靠度；
- \(y=0.01\) 和 \(y=5.0\) 都只被看成 bit 0；
- 通常性能弱于软判决。

## 6.2 浮点软判决 Viterbi

第一版正式基准建议使用：

```text
receivedSymbols 浮点欧氏度量
```

对于候选 BPSK 分支符号 \(x_i\in\{+1,-1\}\)：

\[
M_{\text{soft}}
=
\sum_i(y_i-x_i)^2
\]

也可以使用与 LLR 等价的对数似然度量。

公共 LLR：

\[
LLR_i=\frac{2y_i}{\sigma^2}
\]

第一轮不要直接从 3 bit 或 4 bit 量化开始，否则如果性能异常，很难判断问题来自：

- Viterbi 本身；
- LLR 符号；
- 量化范围；
- 量化步长；
- 饱和策略。

推荐顺序：

```text
浮点软判决基准
→ MATLAB 一致性
→ AWGN 性能确认
→ 再研究量化位宽
```

## 6.3 硬、软判决必须共用同一信道样本

公平链路必须是：

```text
同一 payload
→ 同一卷积编码结果
→ 同一打孔结果
→ 同一 BPSK
→ 同一标准高斯噪声
→ 同一 receivedSymbols
   ├─ hardBits → 硬判决 Viterbi
   └─ receivedSymbols/LLR → 软判决 Viterbi
```

绝对不能：

```text
硬判决单独生成噪声
软判决再单独生成另一组噪声
```

公共规划已明确要求硬、软 Viterbi 使用相同原始输入、编码结果、接收符号、噪声、SNR 和停止规则。fileciteturn0file8L1-L20

---

# 七、SNR 横轴应该怎样定义

你要求科研图横轴显示：

```text
SNR
```

这个要求可以执行，但程序内部必须明确它究竟代表什么。

建议把本项目图中的 SNR 冻结为：

\[
\frac{E_s}{N_0}
\]

也就是 BPSK 每个发送符号能量与噪声谱密度之比。

由于 BPSK 每个编码 bit 对应一个符号，且符号能量归一化为 1，有：

\[
\mathrm{SNR}_{\mathrm{dB}}
=
\left(\frac{E_b}{N_0}\right)_{\mathrm{dB}}
+
10\log_{10}(R_{\text{actual}})
\]

因此：

\[
\left(\frac{E_b}{N_0}\right)_{\mathrm{dB}}
=
\mathrm{SNR}_{\mathrm{dB}}
-
10\log_{10}(R_{\text{actual}})
\]

公共 AWGN 公式：

\[
\sigma^2
=
\frac{1}
{2R_{\text{actual}}
10^{(E_b/N_0)_{\mathrm{dB}}/10}}
\]

将换算关系代入：

\[
\sigma^2
=
\frac{1}
{2\cdot10^{\mathrm{SNR}_{\mathrm{dB}}/10}}
\]

这意味着：

- 在统一 SNR 横轴下，所有 Case 的实际符号噪声强度一致；
- 每个 Case 对应的 \(E_b/N_0\) 会因实际码率不同而不同；
- 不能把同一个数值同时当作 SNR 和 \(E_b/N_0\)。

正式图片横轴：

```text
SNR (dB)
```

结果 CSV 必须同时保留：

```text
snrDb
ebN0Db
actualRate
sigmaSquared
```

checker 逐点验证：

```text
ebN0Db = snrDb - 10*log10(actualRate)
sigmaSquared = 1/(2*10^(snrDb/10))
```

这里需要特别注意一个常见问题：

> 如果代码直接用 \(\sigma^2=1/(2R10^{SNR/10})\)，同时又把横轴称为 SNR，那么实际上代码把横轴当成了 \(E_b/N_0\)，术语就会错位。

因此，Stage01 必须一次性冻结，不允许绘图脚本和 C++ runner 各自理解。

---

# 八、“整块编码和按时隙比特长度分块”到底是什么意思

这是 CC 规划里最容易混淆的部分。

## 8.1 整块零尾编码

把整个 300 bit 电文看成一个完整任务：

```text
300 bit payload
→ 加 6 个零尾 bit
→ 一次卷积编码
→ 得到完整码字
→ 完整接收
→ 从起始零状态译码
→ 强制从最终零状态回溯
→ 输出 300 bit
```

特点：

- 起始状态已知；
- 最终状态已知；
- 边界清晰；
- MATLAB 对照容易；
- FER 定义简单；
- 需要等待整个码字接收后再完整输出；
- 6 个尾比特产生额外发送开销。

## 8.2 错误的“每时隙独立零尾分块”

假设把 300 bit 分成 3 个 100 bit 时隙，如果每个时隙都独立做：

```text
100 bit + 6 个尾 bit
```

那么总编码器输入变成：

\[
3\times(100+6)=318
\]

母码发送长度变成：

\[
2\times318=636
\]

相比整个 300 bit 只加一次尾比特的 612 bit，多发送：

\[
636-612=24\text{ bit}
\]

这就是分块边界反复清零带来的效率损失。

老师提出连续编码和滑窗译码，正是为了避免每个时隙都重新增加尾比特。

## 8.3 正确的按时隙连续编码

仍然把 300 bit 分成若干时隙，例如：

```text
slot 0：100 bit
slot 1：100 bit
slot 2：100 bit
```

但编码器状态跨时隙保持：

```text
初始状态 0
→ 编码 slot 0 后保留状态 S1
→ 从 S1 继续编码 slot 1
→ 编码后保留状态 S2
→ 从 S2 继续编码 slot 2
```

中间时隙不加 6 个尾比特。

接收端不是分别把每个时隙当成独立块，而是维护连续的 Viterbi 路径度量，并使用滑窗逐步输出已经稳定的历史 bit。

示意：

```text
连续接收：
[slot 0][slot 1][slot 2][slot 3]...

窗口 1：
[slot 0][slot 1]

窗口 2：
       [slot 1][slot 2]

窗口 3：
              [slot 2][slot 3]
```

每次窗口向前滑动，只输出已经具有足够回溯深度、路径基本收敛的那一部分 bit。

## 8.4 “分块”分的是传输时序，不一定分断编码状态

这里最重要的理解是：

> 按时隙分块不等于把卷积码拆成多个互不相关的小码块。

它通常是：

- 发送层面按时隙切片；
- 编码器状态连续；
- 接收缓存按窗口处理；
- 译码结果逐步输出；
- 不在每个时隙重新归零。

所以建议目录使用：

```text
continuous
```

比单纯使用：

```text
segmented
```

更准确。

---

# 九、CC 中真正需要比较哪些参数

不能只比较“整块”和“分块”两个名字。需要把组织方式拆成可测量的参数。

## 9.1 码率参数

```text
1/2
2/3
3/4
actualRate
N_transmitted
```

## 9.2 译码输入参数

```text
HARD
SOFT_FLOAT
SOFT_QUANTIZED_3BIT
SOFT_QUANTIZED_4BIT
SOFT_QUANTIZED_6BIT
```

量化实验建议作为扩展，不要和浮点基线同时起步。

## 9.3 回溯深度

建议预扫描：

\[
D_{\mathrm{tb}}
\in
\{5K,7K,10K\}
\]

对于 \(K=7\)：

```text
35
49
70
```

还可以加入：

```text
42
56
64
```

但不要一开始组合过多。

## 9.4 时隙长度

老师附件没有给出具体“时隙内比特承载长度”，因此现在不能假装这是已冻结参数。

初步预扫描可研究：

```text
slotPayloadBits ∈ {50, 75, 100, 150}
```

这些都能整除或较自然地分割 300 bit。

更推荐主候选：

```text
50 bit × 6 slots
100 bit × 3 slots
150 bit × 2 slots
```

其中 100 bit 是最直观的基准。

正式时隙长度最终应根据系统真实时隙承载能力冻结；若老师没有提供，就必须在报告中明确写成“仿真设计参数”，不能写成“业务已知参数”。

## 9.5 滑窗长度

窗口长度必须大于回溯深度，并留出本次输出区间。

建议用输入信息 bit 数表示：

```text
windowInputBits
```

初步候选：

```text
windowInputBits ∈ {64, 96, 128, 192}
```

或者与时隙绑定：

```text
1 slot
2 slots
3 slots
```

但需要满足：

\[
W>D_{\mathrm{tb}}
\]

## 9.6 滑动步长

```text
slideStepBits
```

例如：

```text
25
50
100
```

步长越小：

- 输出更频繁；
- 控制开销更高；
- 缓存重叠更多。

步长越大：

- 运算调用次数少；
- 首次输出和后续批量时延更大。

## 9.7 终止策略

需要至少区分：

```text
BLOCK_ZERO_TAIL
CONTINUOUS_UNTERMINATED
CONTINUOUS_FINAL_TAIL
```

对于有限的 300 bit 实验，为了最终能够精确完成整帧 FER 统计，可采用：

```text
中间时隙不终止
最后一个时隙后统一加 6 个尾 bit
```

这样既模拟连续时隙，又能在 300 bit 结束时收口。

后续真正的长连续流实验，再研究完全不终止的稳态输出。

## 9.8 最终对比指标

| 类别 | 指标 |
|---|---|
| 可靠性 | BER、FER、边界 BER、首尾区 BER |
| 长度 | 母码长度、打孔后长度、尾比特开销 |
| 码率 | actualRate |
| 实时性 | 首比特输出时延、平均输出时延、P95、最大时延 |
| 吞吐 | payload bit/s、decoded bit/s |
| 内存 | 路径度量内存、幸存路径内存、窗口缓存 |
| 复杂度 | ACS 次数、分支度量次数、回溯操作数 |
| 连续性 | 是否保持状态、是否允许跨时隙输出 |
| 边界效应 | 时隙开始与结束附近的误码率 |

---

# 十、有效吞吐如何计算和评估

“有效吞吐”必须区分三种概念，否则容易把发送效率和程序速度混在一起。

## 10.1 信道有效吞吐率

假设每秒发送 \(R_s\) 个 BPSK 符号，每个编码 bit 对应一个符号。

理想无误码情况下：

\[
T_{\text{channel,ideal}}
=
R_s
\frac{K_{\text{payload}}}{N_{\text{transmitted}}}
=
R_sR_{\text{actual}}
\]

单位：

```text
payload bit/s
```

例如符号率为 \(1\text{ Msymbol/s}\)：

### 整块 \(1/2\)

\[
T_{\text{ideal}}
=
10^6\times\frac{300}{612}
\approx490196\text{ bit/s}
\]

实际不是 500 kbit/s，因为有 6 个尾比特。

## 10.2 考虑误帧后的成功有效吞吐

只有整帧 payload 正确才算成功交付时：

\[
T_{\text{goodput}}
=
R_s
R_{\text{actual}}
(1-\mathrm{FER})
\]

也可写成：

\[
T_{\text{goodput}}
=
\frac{
K_{\text{payload}}\times
N_{\text{success frames}}
}{
T_{\text{channel,total}}
}
\]

这通常是最有意义的“有效吞吐”。

例如：

```text
actualRate = 0.4902
symbolRate = 1 Msymbol/s
FER = 0.01
```

则：

\[
T_{\text{goodput}}
=
10^6\times0.4902\times0.99
\approx485294\text{ bit/s}
\]

打孔码可能实际码率更高，但 FER 也可能更高，因此最终 goodput 不一定始终更高。

## 10.3 软件译码吞吐

这是衡量程序或算法处理速度：

\[
T_{\text{decode}}
=
\frac{
\text{成功处理的 payload bit 总数}
}{
\text{纯译码总耗时}
}
\]

或者不考虑正确性，只计算处理能力：

\[
T_{\text{decode,raw}}
=
\frac{
\text{处理的 payload bit 总数}
}{
\text{纯译码总耗时}
}
\]

建议两个都记录：

```text
rawDecodeThroughput_Mbps
successfulDecodeThroughput_Mbps
```

其中：

\[
T_{\text{decode,success}}
=
T_{\text{decode,raw}}(1-\mathrm{FER})
\]

## 10.4 端到端有效吞吐

若已知信道传输时间和算法处理时间：

\[
T_{\text{end-to-end}}
=
\frac{
K_{\text{payload}}\times N_{\text{success}}
}{
T_{\text{tx}}+T_{\text{decode}}+T_{\text{buffer}}
}
\]

对整块方案：

```text
bufferTime 通常接近完整块接收时间
```

对滑窗方案：

```text
可以更早输出部分 bit
但存在窗口缓存和回溯深度
```

因此还应记录：

```text
firstOutputLatency_us
steadyStateOutputInterval_us
fullFrameCompletionLatency_us
```

## 10.5 当前没有真实符号率时怎么办

如果老师还没有给出实际符号率，不应该擅自设一个真实系统速率。

此时报告：

```text
normalizedGoodput = actualRate × (1-FER)
```

它表示：

> 每发送一个 BPSK 编码符号，平均成功交付多少个 payload bit。

同时软件运行结果报告：

```text
rawDecodeThroughput_Mbps
successfulDecodeThroughput_Mbps
```

等后续获得真实符号率，再换算实际链路 goodput。

---

# 十一、科研绘图规范如何落到 CC 中

你的绘图提示词可以作为所有正式绘图脚本的固定约束。

每张图必须由原始结果逐点生成，并保留：

```text
原始 point_results.csv
figure_data.csv
plot_manifest.json
plot_check.md
PNG
文件 SHA256
```

## 11.1 推荐图片

### AWGN 码率对比

```text
300比特卷积码误比特率对比
300比特卷积码误帧率对比
```

横轴：

```text
SNR (dB)
```

纵轴：

```text
BER
FER
```

### 硬软判决对比

```text
卷积码硬软判决误帧率对比
```

图例只写：

```text
1/2 硬判决
1/2 软判决
2/3 硬判决
2/3 软判决
```

不要把：

```text
K=7, G1=171, G2=133, tail=6...
```

全部塞入图例。

这些内容进入 manifest 和配置文件。

### 时延图

```text
卷积码译码时延对比
滑窗长度与译码时延
回溯深度与译码时延
```

纵轴使用：

```text
平均译码时延 (μs)
P95译码时延 (μs)
最大译码时延 (μs)
```

时延用线性坐标。

### 吞吐图

```text
卷积码有效吞吐对比
```

纵轴：

```text
归一化有效吞吐
```

或：

```text
译码吞吐 (Mbit/s)
```

两者不能混画而不说明。

## 11.2 零错误点

CSV 中 BER/FER 必须保持真实值 0。

对数图中单独生成：

```text
plotBer
plotFer
isZeroBerPoint
isZeroFerPoint
```

可以按预先冻结规则使用上界显示，但不能修改原始 BER/FER。

---

# 十二、建议的 S3 Stage 总体规划

下面是一套完整但仍可调整的 Stage 线。

## Stage01：`stage01_cc_contract`

目标：冻结数学和工程定义。

必须冻结：

- 300 bit 主场景；
- \(K=7\)；
- 64 状态；
- \(171/133\) 八进制展开；
- 移位方向；
- 状态编号；
- 输出顺序；
- 起始状态；
- 尾比特；
- SNR 与 \(E_b/N_0\)；
- actualRate；
- BER/FER；
- tie-breaking；
- MATLAB 位序；
- 打孔接口；
- CSV 字段；
- Stage 和结果命名。

Gate：

```text
PASS_STAGE01_CC_CONTRACT
```

---

## Stage02：`stage02_trellis_encoder`

目标：实现 trellis 和 \(1/2\) 母码编码器。

测试：

- 64 状态；
- 每状态两条输入分支；
- next state 唯一；
- 两路输出唯一；
- 全零输入；
- 单位脉冲；
- 固定短序列；
- 随机 300 bit；
- 加 6 个尾 bit 后回零；
- 输出长度 612；
- 与 MATLAB `poly2trellis`、`convenc` 一致。

Gate：

```text
PASS_STAGE02_CC_TRELLIS_ENCODER
```

---

## Stage03：`stage03_hard_viterbi`

目标：整块硬判决 Viterbi。

实现：

- 汉明分支度量；
- ACS；
- 路径度量归一化；
- 幸存路径；
- 终止零状态回溯；
- 确定性 tie-breaking；
- 300 bit payload 恢复。

测试：

- 无噪声；
- 单错误；
- 固定多错误；
- 随机错误；
- 多次运行结果一致；
- MATLAB `vitdec` 对照。

Gate：

```text
PASS_STAGE03_CC_HARD_VITERBI
```

---

## Stage04：`stage04_soft_viterbi`

目标：浮点软判决 Viterbi。

实现：

- 接收符号欧氏度量；
- 或等价 LLR 度量；
- 路径度量有限性；
- NaN/Inf 检查；
- 与硬译码共享 trellis。

测试：

- 无噪声；
- 固定接收符号；
- 固定 LLR；
- 与硬判决共享同一信道；
- MATLAB 对照；
- 相同 receivedSymbols 下软判决不应系统性弱于硬判决。

Gate：

```text
PASS_STAGE04_CC_SOFT_VITERBI
```

---

## Stage05：`stage05_matlab_reference`

目标：建立完整 MATLAB 独立参考。

对比：

- trellis；
- 编码输出；
- 状态轨迹；
- 尾比特；
- 硬译码；
- 软译码；
- 最终 payload；
- 固定噪声帧；
- 输出 bit 顺序。

Gate：

```text
PASS_STAGE05_CC_MATLAB_REFERENCE
```

---

## Stage06：`stage06_puncturing`

目标：冻结 \(2/3\)、\(3/4\) 打孔。

检查：

- 候选图样；
- 周期；
- 输出顺序；
- 尾区处理；
- 实际发送长度；
- actualRate；
- 去打孔；
- 缺失位中性度量；
- 无噪声恢复；
- MATLAB 一致性；
- 小规模性能预扫。

Gate：

```text
PASS_STAGE06_CC_PUNCTURING
```

---

## Stage07：`stage07_block_noiseless`

目标：整块三个码率、两种译码器全组合无噪声回归。

正式 Case：

| Case | 码率 | 译码 |
|---|---|---|
| CC-B-R12-H | \(1/2\) | 硬判决 |
| CC-B-R12-S | \(1/2\) | 软判决 |
| CC-B-R23-H | \(2/3\) | 硬判决 |
| CC-B-R23-S | \(2/3\) | 软判决 |
| CC-B-R34-H | \(3/4\) | 硬判决 |
| CC-B-R34-S | \(3/4\) | 软判决 |

要求：

```text
payload mismatch = 0
length mismatch = 0
non-finite metric = 0
```

Gate：

```text
PASS_STAGE07_CC_BLOCK_NOISELESS
```

---

## Stage08：`stage08_awgn_prescan`

目标：粗定位六个 Case 的 waterfall 区域。

建议：

```text
SNR step = 0.5 dB
minFrames = 300
targetFrameErrors = 30
maxFrames = 2000
```

输出：

- BER/FER 粗曲线；
- 运行时间估计；
- 每个 Case 建议 formal 范围；
- 异常单调性检查；
- 硬软性能关系检查。

Gate：

```text
PASS_STAGE08_CC_AWGN_PRESCAN
```

---

## Stage09：`stage09_awgn_formal`

目标：正式 AWGN 曲线。

建议：

```text
minFrames = 5000
targetFrameErrors = 200
maxFrames = 50000
SNR step = 0.1～0.2 dB
```

最终范围由 Stage08 决定，不应提前固定所有 Case 使用完全相同的无效宽范围。

输出：

- BER；
- FER；
- 置信区间；
- actualRate；
- 发送长度；
- 编码增益；
- 时延；
- normalizedGoodput；
- 科研图及审计文件。

Gate：

```text
PASS_STAGE09_CC_AWGN_FORMAL
```

---

## Stage10：`stage10_traceback_study`

目标：研究回溯深度。

建议主 Case：

```text
1/2 软判决
2/3 软判决
```

候选：

```text
Dtb ∈ {35, 49, 70}
```

指标：

- BER/FER；
- 平均时延；
- P95；
- 最大时延；
- 幸存路径内存；
- 与完整块回溯结果差异。

Gate：

```text
PASS_STAGE10_CC_TRACEBACK_STUDY
```

---

## Stage11：`stage11_soft_quantization`

目标：研究软信息量化。

建议：

```text
float
3 bit
4 bit
6 bit
```

预扫描内容：

- 输入裁剪范围；
- 对称量化；
- 饱和计数；
- 量化零点；
- 性能损失；
- 整数路径度量溢出。

这一阶段不是最早必做，可以放在整块浮点链路完全稳定之后。

Gate：

```text
PASS_STAGE11_CC_SOFT_QUANTIZATION
```

---

## Stage12：`stage12_continuous_encoder`

目标：实现连续编码和跨时隙状态保持。

测试：

- 不同切分方式拼接后，与一次性连续编码结果一致；
- slot 边界不重置状态；
- 状态导入导出一致；
- 中间 slot 不增加尾 bit；
- 最后统一终止时回零。

Gate：

```text
PASS_STAGE12_CC_CONTINUOUS_ENCODER
```

---

## Stage13：`stage13_sliding_window_viterbi`

目标：实现滑窗 Viterbi。

冻结：

- window length；
- traceback depth；
- slide step；
- 输出区间；
- 初始窗口；
- 最终 flush；
- 缓存结构；
- 连续路径度量。

测试：

- 无噪声连续流；
- 固定噪声；
- 与整块 Viterbi 在可比区间一致；
- 不丢 bit；
- 不重复输出；
- slot 边界计数正确。

Gate：

```text
PASS_STAGE13_CC_SLIDING_WINDOW
```

---

## Stage14：`stage14_block_continuous_comparison`

目标：比较整块零尾与连续滑窗。

主比较：

```text
300 bit 整块
50 bit × 6 slots
100 bit × 3 slots
150 bit × 2 slots
```

建议先固定：

```text
1/2 软判决
```

再选择性扩展 \(2/3\)。

指标：

- BER；
- FER；
- 边界 BER；
- firstOutputLatency；
- fullFrameLatency；
- steadyState throughput；
- 尾比特开销；
- 缓存内存；
- ACS 数量。

Gate：

```text
PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON
```

---

## Stage15：`stage15_cc_s3_integration`

目标：完成 S3 总集成与结论。

汇总：

- 三种码率；
- 硬软译码；
- 回溯深度；
- 软量化；
- 整块与连续；
- 滑窗；
- 实际码率；
- 发送长度；
- 时延；
- 吞吐；
- 复杂度。

Gate：

```text
PASS_CC_S3_INTEGRATION
```

---

# 十三、复杂信道与交织暂时放在哪里

当前 S3 的主要目标是把卷积码自身机制建正确。

多径、CFO、短时遮挡不建议立即塞进前面的基础 Stage。

按照老师场景划分：

## S5

等 CC 和 LDPC 各自基线完成后，开展：

```text
卷积码 vs LDPC
AWGN
多径
CFO
短时遮挡
```

## S7

只对 BCH 和 CC 开展：

```text
突发错误
无交织
块交织
行列交织
伪随机交织
```

LDPC 不配置交织。

因此，CC 的突发错误/交织代码可以后续放在：

```text
Task/CC/simulation/stages/S7/
```

不要放入普通 S3 AWGN 基线。

---

# 十四、同步让 Codex 开始 S4-LDPC，需要重点注意什么

你可以让两个 Codex 窗口并行，但必须将“代码并行”与“仓库修改冲突”分开管理。

## 14.1 最重要的风险：两个窗口不能在同一个工作目录里切不同分支

若 CC Codex 和 LDPC Codex 同时操作：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design
```

一个窗口执行 `git switch`，另一个窗口看到的工作区也会跟着变化。

这会导致：

- CC 代码写入 LDPC 分支；
- LDPC 代码写入 CC 分支；
- commit 混杂；
- Codex 对当前分支认知失效；
- 结果目录相互污染。

正确做法是使用两个 Git worktree。

例如：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_CC
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_LDPC
```

分别绑定：

```text
stage01-cc-s3-contract
stage01-ldpc-s4-contract
```

不要手工复制工程目录，应使用：

```powershell
git worktree add ...
```

## 14.2 两个分支都必须来自同一个稳定 main

开始前：

```text
main 必须是已经确认的稳定状态
CC 分支从该 main 建立
LDPC 分支也从同一个 main 建立
```

不要让 LDPC 分支从尚未审查的 CC 分支创建，也不要反过来。

## 14.3 两个窗口不要同时改公共文件

尤其禁止两个窗口同时修改：

```text
Task/Common/
根 CMakeLists.txt
根 README
AGENTS.md
.gitignore
公共结果格式
公共配置定义
```

建议第一轮并行时限定：

### CC 窗口允许修改

```text
Task/CC/**
```

### LDPC 窗口允许修改

```text
Task/LDPC/**
```

公共文件只读。

若确实需要公共接口修改，单独建立：

```text
stage-common-interface-update
```

先完成、审查、合并，再让 CC 和 LDPC 分支同步 main。

## 14.4 不要让两个 Codex 同时使用同一个 build 目录

分别使用：

```text
Task/CC/build/
Task/LDPC/build/
```

不能共用：

```text
build/
Task/build/
```

否则 CMake cache、目标文件和可执行文件可能互相覆盖。

## 14.5 不要让两个实验共享同一个结果目录

必须分别写入：

```text
Task/CC/simulation/stages/S3/stageXX_name/results/
Task/LDPC/simulation/stages/S4/stageXX_name/results/
```

正式结果不能都写入一个顶层 `results/`。

## 14.6 并行初期不要直接跑 formal

两个线路都应先做：

```text
contract
→ 基础结构
→ noiseless
→ MATLAB reference
→ smoke
```

不要一边基础算法尚未验证，一边同时消耗大量时间跑 50000 帧 formal。

## 14.7 对资源占用进行隔离

若两个 Codex 同时编译、MATLAB 验证和仿真，可能出现：

- CPU 满载；
- 内存压力；
- 磁盘 IO 争用；
- 时延测量失真；
- formal 运行速度下降。

因此：

- 功能开发和单元测试可以并行；
- 正式时延测试不要并行运行；
- formal 性能仿真可并行，但时延结果必须在独占或近似空闲环境重测；
- 每个结果记录 CPU、编译模式、线程数和并行状态。

---

# 十五、同步 S4-LDPC 的初步规划

S4 只做 300 bit 高速电文的 LDPC 短块适配，不分块、不加交织。

老师附件规定 LDPC 是卷积码的替换候选，主码长为 480、576 和不超过 640 bit，并需要评估 BP/NMS、迭代次数和时延。fileciteturn0file11L58-L70

结合你当前已经建立的 Direct QC-LDPC 技术路线，建议 S4 分为：

```text
stage01_ldpc_contract
stage02_bg2_zc_selection
stage03_direct_matrix_builder
stage04_hp_rank_encoder
stage05_layered_bp
stage06_layered_nms
stage07_matlab_reference
stage08_noiseless_cases
stage09_awgn_prescan
stage10_awgn_formal
stage11_length_rate_comparison
stage12_s4_integration
```

不过需要特别警惕一处历史要求冲突：

- 你后续技术主线曾明确采用 Direct + Layered SPA/BP；
- 较早老师计划又要求 BP 与 NMS 对比。

因此 S4 开始前必须在 `stage01_ldpc_contract` 写清楚：

```text
主力译码器：Layered SPA/BP
对比译码器：Layered NMS
```

不要让 Codex误解为：

```text
用 NMS 替代 BP 主线
```

另外，LDPC 当前只做：

```text
300 bit
BG2
整块
Direct
不交织
```

不要在 S4 中重新加入：

```text
200 bit 正式主线
Standard 5G NR 速率匹配
LDPC 分块
LDPC 交织
OMS
Offset Min-Sum
神经译码
```

现有参数计划已经明确要求记录目标码长、实际码长、\(Z_c\)、填充、实际码率和 `Hp rank`。fileciteturn0file9L1-L20

---

# 十六、我对你当前执行顺序的建议

当前最合理的并行方式是：

```text
CC 窗口：
S3 Stage01 合同冻结
→ trellis/encoder
→ hard Viterbi
→ soft Viterbi
→ MATLAB
→ puncturing

LDPC 窗口：
S4 Stage01 合同冻结
→ BG2/Zc
→ Direct 矩阵
→ encoder
→ Layered BP/NMS
→ MATLAB
```

两条线路先各自完成无噪声和 MATLAB Gate。

然后再分别进入：

```text
AWGN prescan
→ AWGN formal
```

最后才进入：

```text
S5：CC 与 LDPC 不同信道对比
S6：译码算法专题比较
S7：CC 交织抗突发错误
```

目前不要让 CC Codex 一次性把 S3、S5、S6、S7 全部做完，也不要让 LDPC Codex一开始就跑复杂信道。基础算法一旦存在位序、状态、打孔或 LLR 符号错误，后面的正式结果都会整体失效。

你上传的窗口交接信息已经把 CC 的任务边界、目录规范、实际码率和阶段建议整理得较完整，可作为新窗口背景输入。fileciteturn0file0