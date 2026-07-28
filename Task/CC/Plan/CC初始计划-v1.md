# 卷积码整体实验初步规划

我检查了你上传的任务说明、公共基础规划、参数实施计划和 Git 工作流。卷积码在本项目中的定位很明确：

> 卷积码只用于约 300 bit 的高速电文，是后续与短块 LDPC 对比时的工程基线方案。

老师要求卷积码覆盖：

* 约束长度 (K=7)；
* 母码率 (1/2)；
* 生成多项式 (171_{\mathrm{oct}})、(133_{\mathrm{oct}})；
* (2/3)、(3/4) 打孔码率；
* 硬判决 Viterbi；
* 软判决 Viterbi；
* 300 bit 整块零尾编码；
* 连续编码、按时隙分块和滑窗 Viterbi；
* AWGN 和后续复杂信道；
* 仅在突发错误场景下测试交织。

公共规划也明确要求硬、软 Viterbi 使用完全相同的输入帧、编码码字、噪声、接收符号、SNR 和停止规则，以保证公平比较。

---

## 一、先确定 S3 和 S4 的归属

按照老师附件中的场景划分：

| 场景 | 内容                |
| -- | ----------------- |
| S3 | 高速电文卷积码码长、分块和译码设计 |
| S4 | 高速电文 LDPC 码长设计    |

因此，**本轮卷积码全部放在 S3，不应把卷积码阶段放进 S4**。

建议目录为：

```text
Task/CC/simulation/stages/S3/
```

以后开始 LDPC 时，再使用：

```text
Task/LDPC/simulation/stages/S4/
```

这样目录含义与老师的实验场景一一对应，不会出现卷积码和 LDPC 混放。

---

# 二、建议的 CC 总目录

```text
Task/CC/
├─ block/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ config/
│  ├─ matlab/
│  └─ docs/
│
├─ continuous/
│  ├─ current/
│  │  ├─ include/
│  │  ├─ src/
│  │  └─ tests/
│  ├─ config/
│  ├─ matlab/
│  └─ docs/
│
├─ shared/
│  ├─ include/
│  ├─ src/
│  └─ tests/
│
├─ simulation/
│  ├─ stages/
│  │  └─ S3/
│  │     ├─ stage01_cc_contract/
│  │     ├─ stage02_trellis_encoder/
│  │     ├─ stage03_hard_viterbi/
│  │     ├─ stage04_soft_viterbi/
│  │     ├─ stage05_matlab_reference/
│  │     ├─ stage06_puncturing/
│  │     ├─ stage07_block_noiseless/
│  │     ├─ stage08_awgn_prescan/
│  │     ├─ stage09_awgn_formal/
│  │     ├─ stage10_traceback_study/
│  │     ├─ stage11_continuous_encoder/
│  │     ├─ stage12_sliding_window/
│  │     ├─ stage13_block_continuous_comparison/
│  │     ├─ stage14_complex_channels/
│  │     └─ stage15_burst_interleaving/
│  ├─ scripts/
│  └─ build/
│
└─ README.md
```

这里的核心原则是：

* `block/`：300 bit 整块、尾比特回零；
* `continuous/`：跨时隙保持编码器状态、滑窗译码；
* `shared/`：trellis、打孔图样、路径度量等 CC 内部公共功能；
* 每个实验 Stage 的代码、配置、结果和审计材料放在对应 `stageXX_name` 文件夹内；
* `Task/Common` 只复用已经验证的帧、随机数、BPSK、AWGN、LLR 和统计能力，不放卷积码专用算法。

老师的任务确实要求同时研究整块编码与按时隙分块、连续编码和滑窗译码。

---

# 三、每个 Stage 的固定目录格式

例如：

```text
Task/CC/simulation/stages/S3/stage09_awgn_formal/
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
├─ manifest.json
├─ frozen_config.csv
├─ commands_used.md
├─ changes.patch
├─ git_commit.txt
└─ known_issues.md
```

结果文件全部进入：

```text
stage09_awgn_formal/results/
```

并统一使用阶段名前缀，例如：

```text
stage09_awgn_formal_point_results.csv
stage09_awgn_formal_curve_summary.csv
stage09_awgn_formal_k300_r12_ber.png
stage09_awgn_formal_k300_r12_fer.png
stage09_awgn_formal_plot_manifest.json
stage09_awgn_formal_validation_report.md
```

不允许使用：

```text
result.csv
figure1.png
test.png
output.csv
```

Git 开发仍遵守“一阶段一分支、不得自动合并 main、测试通过后才能提交”的规则。

---

# 四、卷积码参数冻结建议

## 4.1 正式主场景

```text
payloadLength = 300 bit
constraintLength = 7
memory = 6
states = 64
motherRate = 1/2
generator1 = 171 oct
generator2 = 133 oct
initialState = 0
modulation = BPSK
channelBaseline = AWGN
```

卷积码是高速 300 bit 电文主方案，200 bit 只保留程序兼容测试，不作为主要正式曲线。

---

## 4.2 整块终止方式

300 bit payload 后增加：

$$
K-1=6
$$

个零尾比特，使编码器返回全零状态。

因此：

$$
K_{\text{payload}}=300
$$

$$
K_{\text{codec}}=300+6=306
$$

母码率 (1/2) 时：

$$
N_{\text{encoded}}=2\times306=612
$$

实际码率必须按你的统一要求计算：

$$
R_{\text{actual}}
=================

# \frac{K_{\text{payload}}}{N_{\text{transmitted}}}

\frac{300}{612}
\approx0.490196
$$

不能写成简单的 (1/2)。

---

## 4.3 打孔码率

初步研究：

```text
母码率 1/2
打孔码率 2/3
打孔码率 3/4
```

但目前上传文件只规定了目标码率，没有冻结具体打孔图样。任务材料也将“打孔图样未给出”列为正式编程前必须解决的问题。

因此不能直接进入 formal，必须先设置专门的打孔冻结 Stage。

建议候选以输出对为单位，例如：

### (2/3) 候选

```text
P23-A:
1 1
1 0
```

表示两个输入时刻产生 4 个母码 bit，删除其中 1 个，发送 3 个。

### (3/4) 候选

```text
P34-A:
1 1
1 0
0 1
```

表示三个输入时刻产生 6 个母码 bit，删除 2 个，发送 4 个。

正式图样不能仅凭经验选定，应通过以下检查冻结：

* 有效自由距离或低重量错误事件；
* MATLAB 输出一致性；
* 无噪声恢复；
* 打孔和去打孔位置一致；
* 软译码缺失位度量为中性信息；
* 预扫描性能没有异常反转。

打孔后的实际码长必须由程序逐位统计，不能只用“约 459 bit”或“约 408 bit”。

---

# 五、硬判决和软判决 Viterbi

## 5.1 硬判决 Viterbi

输入：

```text
0/1 硬判决比特
```

分支度量使用汉明距离：

$$
M_{\mathrm{hard}}
=================

\sum_i
\mathbf{1}
\left(
r_i\neq c_i
\right)
$$

特点：

* 实现简单；
* 计算量低；
* 丢失接收可靠性；
* 性能预计弱于软判决。

---

## 5.2 软判决 Viterbi

正式基准建议先使用浮点接收符号或浮点 LLR，不应一开始就加入量化误差。

公共 LLR 定义为：

$$
L_i=\frac{2y_i}{\sigma^2}
$$

可以使用与候选输出码字对应的负对数似然或等价欧氏度量。

对于 BPSK 符号候选 (x_i\in{+1,-1})，可使用：

$$
M_{\mathrm{soft}}
=================

\sum_i
(y_i-x_i)^2
$$

或者使用与 LLR 等价的相关度量。

建议顺序：

```text
第一步：浮点软判决基准
第二步：检查与 MATLAB soft Viterbi 一致性
第三步：再研究 3 bit、4 bit、6 bit 等量化
```

老师文件明确要求同时实现硬判决和软判决 Viterbi，并评价软信息量化位宽、路径度量和时延。

---

# 六、SNR 横轴与数学换算

你要求正式图片横轴只显示：

```text
SNR
```

建议沿用 BCH 阶段已使用的统一定义：

$$
\mathrm{SNR}_{\mathrm{dB}}
==========================

\left(\frac{E_b}{N_0}\right)*{\mathrm{dB}}
+
10\log*{10}(R_{\mathrm{actual}})
$$

因此程序若以目标波形 SNR 作为横轴，则内部应计算：

$$
\left(\frac{E_b}{N_0}\right)_{\mathrm{dB}}
==========================================

## \mathrm{SNR}_{\mathrm{dB}}

10\log_{10}(R_{\mathrm{actual}})
$$

AWGN 噪声方差仍使用：

$$
\sigma^2
========

\frac{1}
{2R_{\mathrm{actual}}
10^{(E_b/N_0)_{\mathrm{dB}}/10}}
$$

代入以后：

$$
\sigma^2
========

\frac{1}
{2\cdot10^{\mathrm{SNR}_{\mathrm{dB}}/10}}
$$

这里必须在 Stage01 中冻结一个术语：

> 图中“SNR”定义为 BPSK 每符号能量与噪声谱密度之比 (E_s/N_0)，而不是直接定义为信号功率除以实高斯噪声方差。

否则会出现额外的 3 dB 因子歧义。

每个结果 CSV 同时保存：

```text
snrDb
ebN0Db
actualRate
sigmaSquared
```

并由 checker 逐点验证换算关系。

---

# 七、初步 Stage 规划

## Stage01：`stage01_cc_contract`

### 目标

冻结卷积码所有基础定义。

### 内容

* 300 bit 主场景；
* (K=7)；
* (171/133) 八进制多项式；
* 输入位序；
* 寄存器位序；
* 输出顺序；
* 状态编号；
* 零状态起始；
* 6 个尾比特终止；
* 实际码率；
* SNR 与 (E_b/N_0)；
* BER/FER；
* 打孔接口；
* Viterbi 输出长度；
* MATLAB 对照约定。

### Gate

```text
PASS_STAGE01_CC_CONTRACT
```

---

## Stage02：`stage02_trellis_encoder`

### 目标

实现并验证 64 状态 trellis 和 (1/2) 母码编码器。

### 测试

* 64 个状态；
* 每状态两条分支；
* next-state 唯一；
* 输出 bit 唯一；
* 全零输入；
* 单位脉冲输入；
* 随机 300 bit；
* 尾比特后回到零状态；
* 与 MATLAB `poly2trellis`、`convenc` 对比。

### Gate

```text
PASS_STAGE02_CC_TRELLIS_ENCODER
```

---

## Stage03：`stage03_hard_viterbi`

### 目标

实现整块硬判决 Viterbi。

### 内容

* 汉明分支度量；
* Add-Compare-Select；
* 路径度量归一化；
* 幸存路径；
* 已知终止状态回溯；
* payload 恢复。

### 测试

* 无噪声；
* 单个编码 bit 翻转；
* 多个固定错误；
* 随机错误图样；
* tie-breaking 确定性；
* MATLAB `vitdec` 对比。

### Gate

```text
PASS_STAGE03_CC_HARD_VITERBI
```

---

## Stage04：`stage04_soft_viterbi`

### 目标

实现浮点软判决 Viterbi。

### 内容

* 接收符号度量或 LLR 度量；
* 与硬判决共享相同 trellis；
* 路径度量缩放；
* NaN/Inf 检查；
* 浮点确定性。

### 关键公平性

同一帧必须执行：

```text
同一 payload
→ 同一码字
→ 同一 AWGN
→ 同一 receivedSymbols
├─ hardBits → 硬判决 Viterbi
└─ receivedSymbols/LLR → 软判决 Viterbi
```

### Gate

```text
PASS_STAGE04_CC_SOFT_VITERBI
```

---

## Stage05：`stage05_matlab_reference`

### 目标

建立 C++ 和 MATLAB 独立对照。

### 检查对象

* trellis；
* 母码编码；
* 尾比特；
* 硬译码；
* 软译码；
* decoded payload；
* 路径度量；
* 打孔前固定向量。

### Gate

```text
PASS_STAGE05_CC_MATLAB_REFERENCE
```

---

## Stage06：`stage06_puncturing`

### 目标

冻结 (2/3)、(3/4) 打孔图样。

### 内容

* 打孔；
* 去打孔；
* 实际发送长度；
* 实际码率；
* 硬译码缺失 bit 处理；
* 软译码缺失 bit 使用中性度量；
* 图样周期和尾比特对齐；
* MATLAB 对照。

### Gate

```text
PASS_STAGE06_CC_PUNCTURING
```

---

## Stage07：`stage07_block_noiseless`

### 目标

完成三个码率、两种译码方式的整块无噪声回归。

候选 Case：

| Case       | 组织   | 码率    | 译码  |
| ---------- | ---- | ----- | --- |
| CC-B-R12-H | 整块零尾 | (1/2) | 硬判决 |
| CC-B-R12-S | 整块零尾 | (1/2) | 软判决 |
| CC-B-R23-H | 整块零尾 | (2/3) | 硬判决 |
| CC-B-R23-S | 整块零尾 | (2/3) | 软判决 |
| CC-B-R34-H | 整块零尾 | (3/4) | 硬判决 |
| CC-B-R34-S | 整块零尾 | (3/4) | 软判决 |

### Gate

```text
PASS_STAGE07_CC_BLOCK_NOISELESS
```

---

## Stage08：`stage08_awgn_prescan`

### 目标

寻找六条主要曲线的 waterfall 区域。

### 初步参数

```text
SNR：建议先 0～10 dB
步长：0.5 dB
minFrames：300
targetFrameErrors：30
maxFrames：2000
```

根据实际结果收缩或扩展正式区间。

### 输出

* BER；
* FER；
* 平均译码时延；
* 最大译码时延；
* 每比特译码时间；
* 各码率硬、软判决差异。

### Gate

```text
PASS_STAGE08_CC_AWGN_PRESCAN
```

---

## Stage09：`stage09_awgn_formal`

### 目标

完成整块卷积码基础 AWGN 正式实验。

正式停止规则建议先沿用 BCH 已验证配置：

```text
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
checkpointIntervalFrames = 1000
```

正式 SNR 范围由 Stage08 冻结。为兼顾曲线密度和工作量，建议优先：

```text
0.25 dB 或 0.5 dB 步长
```

不建议未经预扫描就直接使用 0.1 dB 全范围扫描。

### 必须输出

* 300 bit BER；
* 300 bit FER；
* 硬/软 Viterbi 对比；
* (1/2)、(2/3)、(3/4) 码率对比；
* 编码增益；
* 平均、最大、P95 译码时延；
* 码长与实际码率表。

### Gate

```text
PASS_STAGE09_CC_AWGN_FORMAL
```

---

## Stage10：`stage10_traceback_study`

### 目标

研究回溯深度和软信息量化。

候选回溯深度：

$$
D_{\mathrm{tb}}
\in
{5K,7K,10K}
===========

{35,49,70}
$$

也可加入：

```text
42、56、84
```

但应先预扫，避免组合过多。

候选软量化：

```text
浮点
3 bit
4 bit
6 bit
```

输出：

* BER/FER 损失；
* 平均时延；
* 内存；
* 路径度量范围；
* 相对浮点软判决的性能差。

---

## Stage11：`stage11_continuous_encoder`

### 目标

实现跨时隙连续卷积编码。

核心区别：

```text
整块：
每个300 bit帧从零状态开始，尾部回零

连续：
编码器状态跨时隙和帧保持，不添加6个尾比特
```

必须冻结：

* 时隙信息 bit 长度；
* 是否跨 300 bit 电文边界保持状态；
* 时隙编号；
* 状态快照；
* 中断后恢复方式。

当前附件没有给出时隙长度，所以 Stage11 开始前必须先形成假设或向老师确认。

---

## Stage12：`stage12_sliding_window`

### 目标

实现滑窗 Viterbi。

候选参数：

```text
windowLength
tracebackDepth
stepLength
outputDelay
```

输出：

* 稳态 BER/FER；
* 边界 BER；
* 首窗口启动时延；
* 稳态输出时延；
* 平均吞吐率；
* 每时隙缓存量。

---

## Stage13：`stage13_block_continuous_comparison`

### 目标

比较：

```text
整块零尾 Viterbi
连续编码 + 滑窗 Viterbi
```

主要评价：

| 指标     | 整块   | 连续滑窗  |
| ------ | ---- | ----- |
| 尾比特开销  | 有    | 无或较少  |
| 实际码率   | 略低   | 略高    |
| 首次输出时延 | 等待整块 | 等待窗口  |
| 稳态吞吐   | 一般   | 较好    |
| 边界误码   | 边界清晰 | 需重点检查 |
| 实现复杂度  | 较低   | 较高    |

---

## Stage14：`stage14_complex_channels`

### 目标

把已经在 BCH 中验证过的信道模型复用于卷积码：

* 多径；
* 30°整帧累计 CFO；
* 短时遮挡；
* 必要时多普勒。

不应一开始对六个 Case 全组合全部正式运行。建议先用：

```text
R=1/2 硬判决
R=1/2 软判决
R=2/3 软判决
```

作为主线，再根据结果扩展。

---

## Stage15：`stage15_burst_interleaving`

### 目标

只在连续突发错误场景下比较：

```text
无交织
块交织
行列交织
伪随机交织
```

交织不加入普通 AWGN、多径、CFO 或遮挡基础曲线。该限制来自老师的明确要求。

应比较：

* 突发长度；
* 交织深度；
* BER；
* FER；
* 交织缓存；
* 交织时延；
* 滑窗输出时延；
* 整块和连续方案的收益差异。

---

# 八、科研绘图规范

你给出的绘图规则应直接固化为 CC 的 plot checker。

## 8.1 图像横轴

AWGN 类图：

```text
SNR
```

突发错误图：

```text
突发长度 (bit)
```

回溯深度图：

```text
回溯深度 (bit)
```

软量化图：

```text
量化位宽 (bit)
```

滑窗实验图：

```text
窗口长度 (bit)
```

或：

```text
输出时延 (μs)
```

不能所有实验都强制用 SNR 作为横轴。

---

## 8.2 纵轴

```text
BER
FER
译码时延 (μs)
每比特时延 (ns/bit)
吞吐率 (Mbit/s)
内存 (KiB)
```

BER、FER：

```text
对数坐标
```

时延、吞吐和内存：

```text
线性坐标
```

---

## 8.3 零错误点

原始 CSV 必须保留：

```text
BER = 0
FER = 0
```

发布图中：

* 不使用虚假下界替代 0；
* 不在对数坐标留下人工平台；
* 对 0 值点不绘制 marker；
* 曲线在最后一个非零观测点终止；
* manifest 记录零错误点数量；
* 可在报告中给出有限样本上界，但不能伪装成实测 BER/FER。

---

## 8.4 固定视觉映射

建议颜色表示码率：

```text
1/2：蓝色
2/3：橙色
3/4：绿色
```

线型和标记表示译码器：

```text
硬判决：虚线 + 方形
软判决：实线 + 圆形
```

这样读者可立即区分：

* 颜色：码率；
* 线型：硬/软判决。

图例使用：

```text
1/2-硬判决
1/2-软判决
2/3-硬判决
2/3-软判决
3/4-硬判决
3/4-软判决
```

不要出现：

```text
CC_BLOCK_K300_R12_ZERO_TAIL_SOFT_FLOAT
```

---

## 8.5 每图发布资产

每张图必须有：

```text
stageXX_name_xxx.png
stageXX_name_xxx_figure_data.csv
stageXX_name_xxx_plot_manifest.json
```

plot manifest 至少记录：

```text
sourceCsv
sourceSha256
figureDataCsv
figureDataSha256
xColumn
xLabel
xUnit
yColumn
yLabel
yUnit
xTransform
yScale
zeroPolicy
missingValuePolicy
curveCount
legendLabels
colors
lineStyles
markers
dpi
pngSha256
gitCommit
```

checker 至少验证：

* 数据点数量；
* 横轴单调；
* SNR 换算；
* BER/FER 从整数统计复算；
* 无 NaN/Inf；
* 图例唯一；
* 每条曲线有数据；
* PNG 格式；
* 禁止 PDF、SVG、JPG；
* figure-data 与原始结果逐点一致；
* 零值未被替换成虚假非零数；
* 检查失败时不得发布图片。

---

# 九、目前必须在正式编码前冻结的事项

以下四项在上传文件中尚未完全确定，不能由 Codex 随意决定：

1. **卷积码 bit-order 约定**
   (171/133) 的寄存器方向、最高位和最低位含义必须与 MATLAB 对齐。

2. **(2/3)、(3/4) 打孔图样**
   文件只给目标码率，没有给唯一 pattern。

3. **按时隙分块长度**
   文件没有给出每个时隙的信息 bit 数。

4. **滑窗参数**
   窗口长度、滑动步长和回溯深度需要通过预扫描冻结。

因此，下一步不应立刻让 Codex 一次性完成全部卷积码实验。更稳妥的顺序是：

```text
先完成 CC 总体详细规划
→ 冻结 Stage01 参数契约
→ 实现 trellis 和母码编码器
→ 实现硬判决 Viterbi
→ 实现软判决 Viterbi
→ MATLAB 对照
→ 再冻结打孔图样和正式仿真参数
```

---

# 十、总体结论

卷积码实验建议分为三条主线：

```text
主线 A：整块卷积码
K=7，171/133，1/2、2/3、3/4
硬判决和软判决 Viterbi
AWGN 正式曲线

主线 B：连续实时卷积码
跨时隙连续编码
滑窗 Viterbi
窗口、回溯、边界和时延研究

主线 C：信道适应与交织
多径、CFO、遮挡和突发错误
交织只用于突发错误
```

最终卷积码阶段应回答四个核心问题：

1. 软判决相对硬判决获得多少性能收益；
2. 提高到 (2/3)、(3/4) 码率后损失多少可靠性；
3. 连续编码和滑窗译码能否降低端到端实时延迟；
4. 在突发错误下，交织收益是否足以抵消缓存和时延代价。

这套规划与老师附件中的高速卷积码定位、公共仿真定义和你的目录、结果、绘图要求一致。
