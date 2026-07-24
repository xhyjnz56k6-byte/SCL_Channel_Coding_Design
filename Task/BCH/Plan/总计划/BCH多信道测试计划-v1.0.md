下面给出 **S2：低速电文不同信道仿真** 的完整规划。

根据你给出的表格，S2 的任务边界是：

* **输入条件**：AWGN、多径、频偏、短时遮挡、突发错误信道；
* **对比对象**：不同码长、不同组织方式的 BCH 方案；
* **禁止事项**：不引入卷积码、LDPC 或其他信道编码；
* **核心输出**：信道适应性、误帧率、误纠率、突发错误敏感性。

S2 不是重新证明 BCH 编译码器是否正确，而是在 S1 已经完成的编译码和 AWGN 基础上，研究：

> 同一种 BCH 方案换到不同信道后，性能如何变化；不同 BCH 方案对不同失真类型是否敏感。

---

# 一、S2 的总体目标

S1 已经回答了：

```text
在普通 AWGN 下：
不同 BCH 码长、码率和组织方式的 BER、FER、成功率、误纠率和时延如何？
```

S2 要进一步回答：

```text
当错误不再是理想的独立随机错误时：
哪些 BCH 方案最稳定？
哪些方案最容易误纠？
哪些方案对连续错误、频偏和短时遮挡最敏感？
```

建议将 S2 总任务命名为：

```text
BCH 第5组：低速电文多信道适应性与突发错误敏感性仿真
```

建议组级 Gate：

```text
PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION
```

---

# 二、S2 中建议纳入的 BCH 方案

应按 payload 长度分组比较，不能把 200 bit 与 300 bit 的 BER/FER 直接混在一起作为优劣结论。

## 2.1 200 bit 组

| Case     | 结构                     | 编码后长度 |      码率 | 译码方式        |
| -------- | ---------------------- | ----: | ------: | ----------- |
| BCH-S200 | 19×BCH(15,11,1)        |   285 | 200/285 | syndrome 查表 |
| BCH-B200 | shortened BCH(255,207) |   248 | 200/248 | BM+Chien    |

如果后续没有额外增加 200-bit BCH(511,385)，S2 的 200-bit 主线只比较这两个方案。

## 2.2 300 bit 组

| Case         | 结构                     | 编码后长度 |      码率 | 译码方式        |
| ------------ | ---------------------- | ----: | ------: | ----------- |
| BCH-S300     | 28×BCH(15,11,1)        |   420 | 300/420 | syndrome 查表 |
| BCH-B300     | shortened BCH(511,421) |   390 | 300/390 | BM+Chien    |
| BCH-B300-426 | shortened BCH(511,385) |   426 | 300/426 | BM+Chien    |

其中 BCH-B300-426 只有在其 S1 编译码、MATLAB 官方验证和正式 AWGN 结果完成并合并后，才允许进入 S2。

---

# 三、S2 的核心原则

## 3.1 只改变信道，不改变编码器

每个 BCH Case 必须继续使用 S1 冻结的：

* payload 长度；
* 编码后长度；
* 码率；
* filler；
* shortening；
* 生成多项式；
* 译码器；
* 状态定义；
* BER/FER 统计口径。

S2 不能为了适应某种信道而修改 BCH 译码算法。

## 3.2 所有方案使用相同原始 payload

同一信道配置、同一帧号下：

```text
S200 与 B200 使用同一个 200-bit payload
S300、B300、B300-426 使用同一个 300-bit payload
```

## 3.3 尽量使用配对随机条件

在能公平配对的位置上，同一组 Case 应使用：

* 相同标准高斯母噪声；
* 相同多径参数；
* 相同频偏；
* 相同遮挡起点和持续长度；
* 相同突发错误起点和长度。

由于编码长度不同，共同前缀部分可配对，超出部分继续按 bit index 确定性生成。

## 3.4 S2 主线不加入交织

老师表格中 S2 写的是：

```text
不同码长 BCH 方案
不引入其他编码
```

因此 S2 主实验应先固定为：

```text
无交织
```

突发错误敏感性首先测量 BCH 本身的天然抗突发能力。

交织前后比较应放到独立交织实验中，也就是此前规划的 BCH-17，避免混淆：

```text
码本身的抗突发能力
```

和：

```text
交织器带来的错误打散增益
```

---

# 四、S2 的统一链路

不同信道共用同一总体框架：

```text
Common payload frame pool
        ↓
选择 BCH Case
        ↓
BCH 编码
        ↓
BPSK 调制
        ↓
选择信道模型
        ↓
接收端补偿/均衡（仅信道本身要求时）
        ↓
硬判决
        ↓
BCH 译码
        ↓
恢复 payload
        ↓
BER/FER/成功率/误纠率/失败率/时延统计
```

必须保证不同信道的 BCH 译码输入始终是：

```text
硬判决 0/1 比特
```

本阶段不做软判决 BCH。

---

# 五、统一指标

S2 延续 S1 的全部指标。

## 5.1 Payload BER

[
\mathrm{BER}
============

\frac{
\sum_f d_{\mathrm H}
(\boldsymbol u_f,\hat{\boldsymbol u}*f)
}{
N*{\mathrm{frames}}K
}
]

## 5.2 Payload FER

[
\mathrm{FER}
============

\frac{
#{\hat{\boldsymbol u}*f\neq\boldsymbol u_f}
}{
N*{\mathrm{frames}}
}
]

## 5.3 真实译码成功率

[
\mathrm{trueSuccessRate}=1-\mathrm{FER}
]

## 5.4 报告成功率

[
\mathrm{reportedSuccessRate}
============================

\frac{N_{\mathrm{reportedSuccess}}}
{N_{\mathrm{frames}}}
]

## 5.5 误纠率

[
\mathrm{miscorrectionRate}
==========================

\frac{
N_{\mathrm{reportedSuccess}\cap\mathrm{payloadWrong}}
}{
N_{\mathrm{frames}}
}
]

## 5.6 译码器失败率

[
\mathrm{decoderFailureRate}
===========================

\frac{N_{\mathrm{reportedFailure}}}
{N_{\mathrm{frames}}}
]

## 5.7 信道硬判决错误

继续统计：

```text
channelHardBitErrors
channelHardFrameErrors
```

这样可以区分：

```text
信道产生了多少错误
BCH 最终纠正了多少错误
```

---

# 六、S2 新增的信道适应性指标

除了原指标，还应增加以下 S2 专用指标。

## 6.1 相对 AWGN 性能损失

在相同目标 FER 下：

[
L_{\mathrm{channel}}
====================

## E_b/N_0|_{\mathrm{channel}}

E_b/N_0|_{\mathrm{AWGN}}
]

例如：

[
L_{\mathrm{multipath}}(10^{-2})
]

表示达到 FER (10^{-2}) 时，多径信道比 AWGN 多需要多少 dB。

## 6.2 信道适应性评分

不建议直接构造一个没有物理依据的单一总分。

更严谨的方式是输出多维结果：

```text
AWGN损失
多径损失
频偏损失
遮挡损失
突发错误临界长度
误纠率
失败率
时延
```

最后再做定性分级：

```text
强
中
弱
```

## 6.3 突发错误敏感性

定义突发长度 (L_b)，错误起点为 (s)。

对直接 bit-flip burst：

[
r_i=
\begin{cases}
1-c_i,&s\le i<s+L_b,\
c_i,&\text{其他位置}.
\end{cases}
]

输出：

[
\mathrm{FER}(L_b)
]

以及达到指定 FER 的临界突发长度：

[
L_b^{(10^{-1})},\quad
L_b^{(5\times10^{-1})}
]

## 6.4 遮挡敏感性

定义遮挡持续长度：

[
L_{\mathrm{block}}
]

输出：

```text
FER vs 遮挡长度
FER vs 遮挡衰减
误纠率 vs 遮挡长度
```

---

# 七、建议的 Stage 划分

建议将 S2 一次完整任务拆成以下阶段。

```text
S2-01：需求、Case、信道和指标冻结
S2-02：多信道公共基础设施
S2-03：AWGN 基线回归
S2-04：多径信道实验
S2-05：频偏信道实验
S2-06：短时遮挡实验
S2-07：突发错误实验
S2-08：多信道综合比较
S2-09：MATLAB 独立参考与最终审计
```

---

# 八、S2-01：规格冻结

建议 Gate：

```text
PASS_BCH_S2_01_CHANNEL_CONTRACT
```

需要冻结：

* 正式 BCH Case；
* payload 长度；
* 编码后长度；
* 码率；
* 信道模型；
* 信道参数单位；
* 接收端是否均衡；
* 是否已知信道参数；
* 是否使用交织；
* 指标口径；
* 正式帧数；
* 停止规则；
* 随机种子；
* 结果文件 schema。

最关键的是明确：

> S2 比较的是编码方案，还是同时比较接收机算法？

建议 S2 固定接收机为理想已知参数条件，减少接收机算法差异干扰。

---

# 九、S2-02：多信道公共基础设施

建议 Gate：

```text
PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION
```

建立统一接口，例如：

```cpp
enum class BchChannelType {
    Awgn,
    Multipath,
    FrequencyOffset,
    ShortBlockage,
    BurstBitFlip
};
```

统一信道配置：

```cpp
struct ChannelConfig {
    BchChannelType type;
    double ebn0Db;

    MultipathConfig multipath;
    FrequencyOffsetConfig frequencyOffset;
    BlockageConfig blockage;
    BurstConfig burst;
};
```

统一调用：

```cpp
ChannelOutput applyChannel(
    const ChannelConfig& config,
    const std::vector<double>& transmittedSymbols,
    const ChannelKey& key);
```

输出至少包含：

```text
receivedSymbols
standardGaussianSamples
channelParameters
channelStateTrace
affectedStart
affectedLength
```

---

# 十、S2-03：AWGN 基线回归

建议 Gate：

```text
PASS_BCH_S2_03_AWGN_BASELINE_REGRESSION
```

S2 必须先重新调用 S1 已有 AWGN 结果作为基线，但不需要重新跑完整 113 万帧。

建议：

* 读取 BCH-15/BCH-B300-426 正式结果；
* 对每个 Case 选择 3 个代表 SNR；
* 每点固定重新跑 5000 帧；
* 与历史正式结果检查统计相容性；
* 验证新多信道框架没有改变 AWGN 链路。

代表点：

```text
高 FER 区
waterfall 中部
低 FER 区
```

检查：

* noise sigma；
* hard BER；
* BER；
* FER；
* true success；
* miscorrection；
* decoder failure。

如果新框架下 AWGN 与旧框架明显不一致，不得进入其他信道。

---

# 十一、S2-04：多径信道实验

建议 Gate：

```text
PASS_BCH_S2_04_MULTIPATH_CHANNEL
```

## 11.1 建议信道模型

使用离散复基带有限冲激响应信道：

[
y[k]
====

\sum_{\ell=0}^{L_h-1}h_\ell x[k-\ell]
+n[k]
]

建议至少设置三档：

### 轻度多径

```text
h = [1.0, 0.25]
delay = [0,1]
```

### 中度多径

```text
h = [1.0, 0.45, 0.20]
delay = [0,1,3]
```

### 重度多径

```text
h = [1.0, 0.65, 0.35]
delay = [0,1,3]
```

必须对信道能量归一化：

[
\sum_\ell |h_\ell|^2=1
]

否则多径组与 AWGN 的能量不公平。

## 11.2 接收机

必须冻结接收方式。

建议主实验使用：

```text
已知信道冲激响应
+ 统一线性均衡器
```

可以选择：

* ZF equalizer；
* MMSE equalizer。

更推荐 MMSE，因为重度多径下 ZF 会显著放大噪声。

所有 BCH Case 使用完全相同的均衡算法。

## 11.3 多径正式参数

每种多径 profile：

* 先 prescan；
* 正式步长 0.2 dB；
* `minFrames=5000`；
* `targetFrameErrors=200`；
* `maxFrames=50000`。

输出：

```text
BER/FER vs Eb/N0
true/reported success
miscorrection
decoder failure
equalizer output hard BER
相对 AWGN 损失
```

---

# 十二、S2-05：频偏信道实验

建议 Gate：

```text
PASS_BCH_S2_05_FREQUENCY_OFFSET
```

## 12.1 必须切换到复基带表达

频偏不能只在实数 BPSK 值上随便加一个常数。

发送复基带符号：

[
x[k]\in{+1,-1}
]

加入归一化频偏：

[
y[k]
====

x[k]e^{j(2\pi\epsilon k+\phi_0)}
+n[k]
]

其中：

* (\epsilon)：每符号归一化频偏；
* (\phi_0)：初始相位。

## 12.2 主实验建议

建议研究**残余频偏**，也就是接收端完成粗同步后仍剩余的频偏。

频偏档位可以设置为：

```text
ε = 0
ε = 1×10^-4
ε = 5×10^-4
ε = 1×10^-3
ε = 2×10^-3
```

也可以用一帧累计相位旋转量描述：

```text
0°
15°
30°
60°
90°
```

后一种表达对不同码长更容易公平比较。

推荐冻结为：

[
\Delta\phi_{\mathrm{frame}}
===========================

2\pi\epsilon(N-1)
]

这样可比较：

```text
整帧累计旋转 0°、15°、30°、45°、60°、90°
```

## 12.3 接收端条件

需要明确两组：

### 理想补偿基线

接收端知道频偏并完全补偿。

用于验证代码链路。

### 残余频偏实验

不补偿剩余频偏，或只补偿估计值。

S2 主结论建议使用：

```text
给定固定残余频偏
```

不要同时引入复杂同步估计算法，否则比较会变成同步算法比较。

## 12.4 输出

```text
BER/FER vs residual CFO
BER/FER vs Eb/N0
miscorrection vs residual CFO
最大可接受累计相位旋转
各 BCH Case 频偏敏感性
```

---

# 十三、S2-06：短时遮挡实验

建议 Gate：

```text
PASS_BCH_S2_06_SHORT_BLOCKAGE
```

## 13.1 信道模型

短时遮挡本质上是连续一段符号幅度突然下降：

[
y[k]
====

a[k]x[k]+n[k]
]

其中：

[
a[k]=
\begin{cases}
A_{\mathrm{block}},&
s\le k<s+L_{\mathrm{block}},\
1,&\text{其他}.
\end{cases}
]

建议衰减档位：

```text
0 dB：无衰减
-6 dB
-12 dB
-20 dB
完全遮挡：A=0
```

遮挡长度：

```text
1
2
4
8
16
32
64 symbols
```

## 13.2 起点策略

至少研究：

* 均匀随机起点；
* 码字前部；
* 码字中部；
* 码字尾部。

对分块码还应特别记录遮挡覆盖了多少个子块。

## 13.3 为什么该实验重要

对于分块码：

* 若遮挡集中在一个 15-bit 子块，可能造成大量局部错误；
* 若跨越多个子块，错误可能被分散。

对于整块码：

* 只看整块总错误及其译码结构；
* 不受分块边界直接限制。

因此遮挡位置相对于分块边界，是 S2 的关键诊断量。

## 13.4 输出

```text
FER vs blockage length
FER vs blockage attenuation
miscorrection vs blockage length
decoder failure vs blockage length
payload position sensitivity
block boundary sensitivity
```

---

# 十四、S2-07：突发错误信道

建议 Gate：

```text
PASS_BCH_S2_07_BURST_ERROR_CHANNEL
```

## 14.1 主模型：确定性连续 bit flip

在无 AWGN 或固定背景 AWGN 下，对硬判决比特连续翻转：

```text
起点 s
突发长度 Lb
连续 Lb bit 取反
```

建议分成两套实验。

### 纯突发错误

```text
AWGN关闭
只注入连续bit flip
```

用于直接观察 BCH 结构的突发纠错能力。

### AWGN + 突发错误

```text
背景 AWGN
+
连续 bit flip
```

用于更接近实际信道。

## 14.2 突发长度

建议：

```text
Lb = 1,2,3,4,5,6,8,10,12,16,20,24,32,48,64
```

对分块 BCH 增加关键边界：

```text
14,15,16
29,30,31
```

用于观察突发是否跨越 BCH(15,11) 子块边界。

## 14.3 起点

每个长度至少覆盖：

* 起点 0；
* 末尾；
* 子块内部；
* 子块边界前；
* 子块边界上；
* 随机起点至少 100 个。

## 14.4 输出

```text
FER vs burst length
true success vs burst length
miscorrection vs burst length
decoder failure vs burst length
FER heatmap-like CSV：start × length
临界突发长度
分块边界敏感性
```

图片仍然只输出普通 PNG 线图；需要二维展示时可以使用 matplotlib 的 `imshow` 或 `pcolormesh`，但每张图独立 figure。

## 14.5 不加入交织

本阶段只测：

```text
BCH 自身对突发错误的敏感性
```

交织应在后续单独实验中使用同一突发输入进行前后对比。

---

# 十五、正式实验规模

S2 包含很多参数维度，若每个组合都直接跑 50000 帧，规模会失控。

建议采用三级策略。

## 15.1 Smoke

每个信道模型、每个 BCH Case：

```text
3～5个代表参数
每点500帧
```

目的：

* 链路正确；
* 参数方向正确；
* 无 NaN/Inf；
* 趋势合理。

## 15.2 Prescan

每个信道强度档位：

```text
每点2000帧
```

用于选择：

* 有价值的 SNR 范围；
* 有价值的信道参数；
* waterfall 区域。

## 15.3 Formal

只对最终冻结的关键组合运行：

```text
minFrames = 5000
targetFrameErrors = 200
maxFrames = 50000
```

建议每种信道正式保留：

* 轻度；
* 中度；
* 重度；

三个 profile，而不是把所有 prescan 参数都进入正式长跑。

---

# 十六、建议的正式实验矩阵

## 16.1 AWGN

直接复用 S1 正式结果。

## 16.2 多径

```text
3个多径 profile
× 每个 payload 组所有 BCH Case
× waterfall SNR 网格
```

## 16.3 频偏

建议固定三个代表 Eb/N0：

```text
低端
waterfall中点
高端
```

再扫描：

```text
累计相位旋转 0°～90°
```

避免同时完整扫描二维 SNR×CFO 导致规模过大。

然后选择中度频偏做完整 FER 曲线。

## 16.4 短时遮挡

建议固定两个代表 Eb/N0：

```text
waterfall中点
高SNR低误码点
```

扫描：

```text
遮挡衰减
遮挡长度
```

再挑选一个典型遮挡 profile 跑完整 SNR 曲线。

## 16.5 突发错误

纯 burst 实验不需要扫描 Eb/N0。

固定：

```text
无 AWGN
```

扫描：

```text
burst start
burst length
```

另外选择一个背景 SNR，运行：

```text
AWGN + burst
```

---

# 十七、MATLAB 验证规划

S2 不一定需要 MATLAB 重跑全部正式大规模实验，但必须完成独立信道参考。

建议每种信道至少进行：

```text
固定 payload
固定编码码字
固定噪声/信道参数
固定信道输出
固定硬判决结果
```

逐字段比较：

* channel output；
* equalized symbols；
* hard bits；
* channel hard bit errors；
* decoded payload；
* FER；
* true success；
* reported success；
* miscorrection；
* failure。

## 17.1 AWGN

已有 BCH-16V 可复用。

## 17.2 多径

MATLAB 使用：

```text
filter / conv
+
相同 MMSE/ZF 均衡算法
```

## 17.3 频偏

MATLAB 按相同复指数旋转。

## 17.4 遮挡

MATLAB 使用相同 attenuation mask。

## 17.5 Burst

MATLAB 对相同位置连续翻转。

S2 的 MATLAB 重点是验证信道和接收处理，不需要再次重新证明 BCH 核心。

---

# 十八、S2-08：综合比较

建议 Gate：

```text
PASS_BCH_S2_08_CHANNEL_ADAPTATION_COMPARISON
```

## 18.1 按 payload 长度分别比较

### 200 bit

```text
S200 vs B200
```

### 300 bit

```text
S300 vs B300 vs B300-426
```

## 18.2 对每种信道输出

```text
BER
FER
true success
reported success
miscorrection
decoder failure
相对AWGN损失
平均译码时延
P95/P99时延
```

## 18.3 适应性总结表

建议最终表：

| Payload | Case | AWGN | 多径 | 频偏 | 遮挡 | Burst | 误纠风险 | 时延 |
| ------- | ---- | ---- | -- | -- | -- | ----- | ---- | -- |

其中每个信道可记录：

```text
目标 FER 所需 Eb/N0
相对 AWGN 损失
或者固定条件下 FER
```

不要用一个没有依据的“总分”替代原始结果。

---

# 十九、建议输出图片

所有图片继续使用：

```text
Python matplotlib
PNG only
```

## 19.1 多径

```text
bch_s2_200bit_multipath_fer.png
bch_s2_200bit_multipath_ber.png
bch_s2_300bit_multipath_fer.png
bch_s2_300bit_multipath_ber.png
bch_s2_multipath_awgn_loss.png
```

## 19.2 频偏

```text
bch_s2_200bit_cfo_fer.png
bch_s2_300bit_cfo_fer.png
bch_s2_cfo_miscorrection.png
bch_s2_cfo_tolerance.png
```

## 19.3 遮挡

```text
bch_s2_200bit_blockage_fer_vs_length.png
bch_s2_300bit_blockage_fer_vs_length.png
bch_s2_blockage_fer_vs_attenuation.png
bch_s2_blockage_position_sensitivity.png
```

## 19.4 突发错误

```text
bch_s2_200bit_burst_fer_vs_length.png
bch_s2_300bit_burst_fer_vs_length.png
bch_s2_burst_miscorrection_vs_length.png
bch_s2_burst_boundary_sensitivity.png
```

## 19.5 综合

```text
bch_s2_200bit_channel_adaptation.png
bch_s2_300bit_channel_adaptation.png
bch_s2_awgn_loss_comparison.png
bch_s2_miscorrection_comparison.png
```

每个 Case 在所有图片中保持统一颜色、marker 和 line style。

---

# 二十、详细进度条

S2 参数维度多，必须显示层级进度。

建议层级：

```text
Stage
→ Channel
→ Channel profile
→ BCH Case
→ SNR/参数点
→ Frame
```

显示：

```text
stage
channel
profile
case
Eb/N0
channel parameter
processedFrames
maxFrames
frameErrors
targetFrameErrors
BER
FER
miscorrectionRate
decoderFailureRate
speed
elapsed
ETA
checkpoint
shard
```

示例：

```text
[S2-04][MULTIPATH-MEDIUM][BCH-B300][6.8 dB]
frames 18240/50000
FE 143/200
FER 7.84e-3
miscorr 2
speed 930 frame/s
ETA 00:00:34
```

必须支持：

```text
--progress
--no-progress
--progress-refresh-seconds
progress.jsonl
```

---

# 二十一、Checkpoint、Resume 和 Shard

继续复用 S1 的基础设施。

Checkpoint config hash 必须增加：

```text
channelType
channelProfileId
multipath taps
equalizerType
frequencyOffset
initialPhase
blockageStartPolicy
blockageLength
blockageAttenuation
burstStartPolicy
burstLength
backgroundAwgnEnabled
```

否则不同信道配置可能错误恢复同一 checkpoint。

Shard 合并必须检查：

* 信道配置一致；
* Case 一致；
* 参数一致；
* frame range 无重叠；
* 无遗漏；
* seed 和 noise policy 一致。

---

# 二十二、建议目录

```text
Task/BCH/channel_simulation/
├─ current/
│  ├─ include/
│  ├─ src/
│  ├─ tests/
│  └─ CMakeLists.txt
├─ configs/
│  ├─ awgn/
│  ├─ multipath/
│  ├─ frequency_offset/
│  ├─ blockage/
│  └─ burst/
├─ scripts/
├─ matlab/
├─ results/
│  ├─ smoke/
│  ├─ prescan/
│  ├─ formal/
│  └─ comparison/
└─ stages/
   ├─ s2_01_channel_contract/
   ├─ s2_02_multi_channel_foundation/
   ├─ s2_03_awgn_regression/
   ├─ s2_04_multipath/
   ├─ s2_05_frequency_offset/
   ├─ s2_06_short_blockage/
   ├─ s2_07_burst_error/
   ├─ s2_08_channel_adaptation_comparison/
   ├─ s2_09_matlab_reference/
   └─ s2_multi_channel_adaptation/
```

如果仓库已有 `Task/BCH/simulation`，优先在现有目录下扩展 `channels/`，不要创建重复 runner。

---

# 二十三、建议 Gate

```text
PASS_BCH_S2_01_CHANNEL_CONTRACT
PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION
PASS_BCH_S2_03_AWGN_BASELINE_REGRESSION
PASS_BCH_S2_04_MULTIPATH_CHANNEL
PASS_BCH_S2_05_FREQUENCY_OFFSET
PASS_BCH_S2_06_SHORT_BLOCKAGE
PASS_BCH_S2_07_BURST_ERROR_CHANNEL
PASS_BCH_S2_08_CHANNEL_ADAPTATION_COMPARISON
PASS_BCH_S2_09_MATLAB_CHANNEL_REFERENCE
```

最终：

```text
PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION
```

---

# 二十四、S2 最终应回答的问题

完成后，报告必须明确回答：

1. 哪一种 BCH 方案在 AWGN 下最好？
2. 哪一种在多径条件下性能下降最少？
3. 哪一种对残余频偏最敏感？
4. 哪一种对短时遮挡最敏感？
5. 分块 BCH 是否容易因局部遮挡或突发错误产生误纠？
6. 整块 BCH 是否因为联合纠错在随机错误下更优，但在长突发下也会迅速超过 (t)？
7. BCH-B300-426 相对 BCH-B300 的额外纠错能力是否值得其更低码率和更高时延？
8. 不同 Case 的误纠率与显式失败率有什么差别？
9. 哪种方案适合随机 AWGN？
10. 哪种方案适合存在连续错误或瞬时遮挡的低速通信系统？

---

# 二十五、建议的最终结论表达方式

S2 不能提前写死“哪一个最好”。

最终结论应按场景给出，例如：

```text
在独立随机 AWGN 下……
在已均衡多径下……
在残余频偏条件下……
在短时深衰落条件下……
在连续 bit-flip 突发条件下……
```

尤其不能用 AWGN 结果直接推断 burst 性能。

---

# 最终进度定位

S2 完成后，BCH 主线将达到：

```text
S1：不同 BCH 码长设计与 AWGN 性能比较——完成
S2：不同信道适应性与突发错误敏感性——完成
交织增益独立实验——待完成或作为 S2 后续扩展
最终 BCH 综合报告——待收口
```

其中 S2 最关键的科学价值是：

> 把“某个 BCH 在 AWGN 曲线更好”扩展为“这个 BCH 在不同失真机制下是否仍然稳定”，并区分随机错误、局部集中错误和连续突发错误对分块码与整块码的不同影响。
