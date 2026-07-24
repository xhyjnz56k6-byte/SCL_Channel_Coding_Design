下面按照你现在的六点要求，重新冻结 S2 规划。整体思路是：

```text
不再重复跑 AWGN
→ 直接复用 S1 已完成的 AWGN 正式结果作为基线
→ 依次完成多径、频偏、短时遮挡、突发错误
→ 最后统一与 AWGN 基线做信道适应性比较
```

这样更合理，也能避免重复消耗大量时间。

# 一、S2 总体任务重新冻结

S2 的核心目标不再是“再做一次 AWGN”，而是研究：

> 已经在 AWGN 下验证过的不同 BCH 方案，遇到非理想信道后，性能下降多少；哪些方案对多径、频偏、遮挡和突发错误更敏感。

正式参与比较的 BCH 方案按 payload 分组。

## 200 bit 组

| Case     | 结构                     | 编码长度 |        码率 |
| -------- | ---------------------- | ---: | --------: |
| BCH-S200 | 19×BCH(15,11,1)        |  285 | (200/285) |
| BCH-B200 | shortened BCH(255,207) |  248 | (200/248) |

## 300 bit 组

| Case         | 结构                     | 编码长度 |        码率 |
| ------------ | ---------------------- | ---: | --------: |
| BCH-S300     | 28×BCH(15,11,1)        |  420 | (300/420) |
| BCH-B300     | shortened BCH(511,421) |  390 | (300/390) |
| BCH-B300-426 | shortened BCH(511,385) |  426 | (300/426) |

200 bit 与 300 bit 的 BER、FER 不直接混在一张主性能图中比较。

---

# 二、重新调整后的 Stage

建议将 S2 改成：

```text
S2-01：S2 规格、Case、信道与指标冻结
S2-02：多信道公共基础设施
S2-03：跳过，不重新运行 AWGN
S2-04：固定多径 + MMSE 均衡实验
S2-05：频偏实验
S2-06：短时遮挡实验
S2-07：突发错误敏感性实验
S2-08：多信道与 AWGN 综合比较
S2-09：MATLAB 信道链路参考与最终审计
```

建议最终 Gate：

```text
PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION
```

其中原来的 S2-03 不删除编号，而是明确标记为：

```text
SKIPPED_BCH_S2_03_AWGN_RERUN
REUSED_S1_FORMAL_AWGN_BASELINE
```

这样审计记录清楚：不是忘了做，而是经用户确认主动复用 S1 结果。

---

# 三、AWGN 如何作为最终基线

不再运行 AWGN，但必须读取并冻结已有正式结果：

* S200、B200；
* S300、B300、B300-426；
* 原始 payload (E_b/N_0)；
* BER；
* FER；
* true success；
* reported success；
* miscorrection；
* decoder failure；
* 时延。

读取时必须验证：

```text
文件路径
SHA-256
Case 参数
payload 长度
编码长度
码率
SNR 网格
正式帧数
停止条件
结果 schema
```

最终把 AWGN 当作“理想参考信道”：

[
\mathrm{Loss}_{\mathrm{channel}}
================================

## \mathrm{SNR}_{\mathrm{channel}}

\mathrm{SNR}_{\mathrm{AWGN}}
]

但只有当两条曲线都真实夹住同一个目标 FER 时才允许计算。

---

# 四、老师要求的三个输出指标如何定义

老师要求：

1. 信道适应性；
2. FER；
3. 突发错误敏感性。

这三个指标不是完全独立的，需要建立清晰的统计体系。

# 五、FER 如何统计

第 (i) 帧原始 payload：

[
\boldsymbol u_i
]

译码后 payload：

[
\hat{\boldsymbol u}_i
]

定义帧错误指示量：

[
F_i=
\mathbf 1
\left(
\hat{\boldsymbol u}_i\neq\boldsymbol u_i
\right)
]

则：

[
\boxed{
\mathrm{FER}
============

\frac{1}{N_{\mathrm f}}
\sum_{i=1}^{N_{\mathrm f}}F_i
}
]

也就是：

[
\boxed{
\mathrm{FER}
============

\frac{\text{译码后 payload 至少有 1 bit 错误的帧数}}
{\text{总处理帧数}}
}
]

这一口径与 S1 完全一致。

注意：

* 不比较编码码字；
* 不统计校验位；
* 不统计 filler；
* 不统计虚拟缩短位；
* 只看最终恢复的 200 bit 或 300 bit payload。

同时保留：

[
\mathrm{trueSuccessRate}=1-\mathrm{FER}
]

以及：

[
\mathrm{miscorrectionRate}
==========================

\frac{
N_{\mathrm{reportedSuccess}\cap\mathrm{payloadWrong}}
}{
N_{\mathrm f}
}
]

非理想信道下，误纠率非常重要，因为连续错误和相干失真更容易产生“译码器报告成功，但 payload 实际错误”的情况。

---

# 六、“信道适应性”到底是什么

“信道适应性”不是一个天然唯一的数学指标。

不能随意定义一个分数，例如：

```text
适应性 = 0.4×FER + 0.3×BER + ...
```

这种加权总分缺少物理依据。

更严格的方式是把信道适应性定义为：

> 某个 BCH 方案相对于 AWGN 基线，在特定信道下性能退化的程度。

建议使用四类指标共同表征。

## 6.1 固定目标 FER 下的 SNR 损失

例如目标：

[
\mathrm{FER}=10^{-1}
]

[
\mathrm{FER}=10^{-2}
]

对于某信道 (c)，定义：

[
\boxed{
L_c(F^\star)
============

## \mathrm{SNR}_{c}(F^\star)

\mathrm{SNR}_{\mathrm{AWGN}}(F^\star)
}
]

其中 (F^\star) 是目标 FER。

例如：

[
L_{\mathrm{multipath}}(10^{-2})=1.4\text{ dB}
]

含义是：

> 达到 FER (10^{-2})，多径信道比 AWGN 多需要 1.4 dB。

数值越小，说明信道适应性越强。

## 6.2 固定 SNR 下的 FER 放大量

选定共同 SNR：

[
\gamma_0
]

定义：

[
\boxed{
G_c(\gamma_0)
=============

\frac{
\mathrm{FER}*{c}(\gamma_0)
}{
\mathrm{FER}*{\mathrm{AWGN}}(\gamma_0)
}
}
]

也可以用对数形式：

[
\Delta\log_{10}\mathrm{FER}
===========================

## \log_{10}\mathrm{FER}_{c}

\log_{10}\mathrm{FER}_{\mathrm{AWGN}}
]

例如：

```text
AWGN FER = 1e-3
多径 FER = 2e-2
放大量 = 20
```

但如果 AWGN FER 为 0，则不能直接相除，应使用置信上界或停止计算。

## 6.3 固定信道强度下的相对性能排序

例如在固定：

* 多径 profile；
* 频偏 30°；
* 遮挡长度 16；
* burst 长度 8；

比较各 BCH 方案：

```text
FER
miscorrectionRate
decoderFailureRate
```

这样判断：

> 哪种码在这个失真机制下更稳健？

## 6.4 临界容忍参数

对于不是以 SNR 为主横轴的信道，可以定义临界值。

例如：

### 频偏容忍度

[
\phi_{\max}(F^\star)
]

表示 FER 不超过目标值时，允许的最大整帧累计相位旋转。

### 遮挡容忍长度

[
L_{\mathrm{block,max}}(F^\star)
]

### 突发错误容忍长度

[
L_{\mathrm{burst,max}}(F^\star)
]

这类指标更直观地反映“适应性”。

---

# 七、最终如何比较几种信道

不能把 AWGN、多径、频偏、遮挡和 burst 的所有原始曲线简单画到同一坐标上，因为它们的自变量不同。

建议分成两种比较方式。

## 7.1 同类曲线内部比较

### AWGN 与多径

都可以画：

[
\mathrm{FER}\text{ vs SNR}
]

因此可以直接比较横向性能损失。

### 频偏

主要画：

[
\mathrm{FER}\text{ vs 整帧累计相位旋转}
]

或者固定残余频偏下：

[
\mathrm{FER}\text{ vs SNR}
]

### 遮挡

主要画：

[
\mathrm{FER}\text{ vs 遮挡长度}
]

[
\mathrm{FER}\text{ vs 遮挡衰减}
]

### 突发错误

主要画：

[
\mathrm{FER}\text{ vs burst length}
]

## 7.2 最终统一表格比较

最后输出一张综合表：

| Case | AWGN基线 | 多径损失 | 频偏临界值 | 遮挡临界长度 | Burst临界长度 | 误纠风险 |
| ---- | -----: | ---: | ----: | -----: | --------: | ---: |

例如每个 Case 记录：

```text
AWGN SNR@FER1e-2
多径 SNR@FER1e-2
多径损失
FER@30°残余频偏
最大容忍相位旋转
FER@16-symbol -20dB遮挡
最大容忍遮挡长度
FER@burst length 8
最大容忍burst长度
最大误纠率
```

这样才是真正的“信道适应性比较”。

---

# 八、横轴从比特信噪比改成信噪比

你要求后续输出图中，若原横轴是比特信噪比 (E_b/N_0)，改成信噪比。

需要严格说明你这里所谓的 SNR 是：

[
\boxed{
\frac{E_s}{N_0}
}
]

因为 BPSK 每个编码比特对应一个发送符号，且符号能量设为 (E_s)。

码率：

[
R=\frac{K_{\mathrm{payload}}}{N_{\mathrm{encoded}}}
]

payload 比特能量与符号能量满足：

[
E_s=R E_b
]

因此：

[
\frac{E_s}{N_0}
===============

R\frac{E_b}{N_0}
]

换成 dB：

[
\boxed{
\mathrm{SNR}_{\mathrm{dB}}
==========================

\left(\frac{E_b}{N_0}\right)*{\mathrm{dB}}
+
10\log*{10}(R)
}
]

所以所有后续信道曲线横轴统一写成：

```text
符号信噪比 Es/N0（dB）
```

最好不要只写模糊的“SNR（dB）”。

## 注意

如果仿真程序内部仍以 payload (E_b/N_0) 计算噪声：

[
\sigma^2
========

\frac{1}{2R10^{E_b/N_0/10}}
]

则绘图时做坐标转换即可。

等价地，如果直接使用 (E_s/N_0) 输入，则：

[
\boxed{
\sigma^2
========

\frac{1}
{2\cdot10^{(E_s/N_0)_{\mathrm{dB}}/10}}
}
]

两种方式必须完全等价。

建议程序内部保留成熟的 (E_b/N_0) 逻辑，不修改信道核心；绘图和正式报告转换为：

[
E_s/N_0
]

这样风险最低。

---

# 九、多径实验重新冻结

只使用一组多径：

[
h=[1.0,\ 0.65,\ 0.35]
]

对应 delay：

[
[0,\ 1,\ 3]
]

离散信道为：

[
y[k]
====

h_0x[k]
+
h_1x[k-1]
+
h_2x[k-3]
+
n[k]
]

即：

[
y[k]
====

x[k]
+
0.65x[k-1]
+
0.35x[k-3]
+
n[k]
]

## 9.1 必须归一化信道能量

原始信道能量：

[
E_h
===

1^2+0.65^2+0.35^2
]

[
E_h=1+0.4225+0.1225=1.545
]

如果直接使用未归一化系数，接收信号总能量变大，会导致多径结果可能看起来“比 AWGN 更好”，造成不公平。

因此实际使用：

[
\tilde h_\ell
=============

\frac{h_\ell}{\sqrt{1.545}}
]

约为：

[
\tilde h
\approx
[0.8045,\ 0.5229,\ 0.2816]
]

正式报告应同时记录：

```text
raw taps = [1.0,0.65,0.35]
normalized taps = [...]
delays = [0,1,3]
normalization = unit-energy
```

---

# 十、多径接收机：MMSE 均衡器

统一使用 MMSE，不再测试 ZF。

信道模型：

[
\boldsymbol y
=============

\boldsymbol H\boldsymbol x
+
\boldsymbol n
]

线性 MMSE 均衡器一般形式：

[
\boxed{
\boldsymbol W_{\mathrm{MMSE}}
=============================

\left(
\boldsymbol H^{H}\boldsymbol H
+
\sigma_n^2\boldsymbol I
\right)^{-1}
\boldsymbol H^{H}
}
]

均衡输出：

[
\hat{\boldsymbol x}
===================

\boldsymbol W_{\mathrm{MMSE}}\boldsymbol y
]

然后硬判决：

[
\hat c_k=
\begin{cases}
0,&\Re{\hat x_k}\ge0,\
1,&\Re{\hat x_k}<0.
\end{cases}
]

## 10.1 必须冻结边界处理

卷积信道会产生尾部延长，必须明确：

* 是否零填充；
* 输出长度；
* 矩阵尺寸；
* 是否保留尾部观测；
* 最终恢复哪 (N) 个发送符号。

建议采用：

```text
发送码字前后零填充
保留完整卷积输出
MMSE 联合估计原 N 个符号
最终只输出原 N 个符号估计
```

不要简单截掉尾部后再均衡，否则会损失信息并引入边界偏差。

## 10.2 已知信道

S2 主实验固定：

```text
接收端理想已知 h 和 delay
```

这样研究的是 BCH 对多径残留错误的适应性，而不是信道估计算法优劣。

---

# 十一、多径实验流程

```text
payload
→ BCH encode
→ BPSK
→ unit-energy multipath convolution
→ AWGN
→ known-channel MMSE equalization
→ hard decision
→ BCH decode
→ payload metrics
```

正式对比：

```text
AWGN baseline
vs
multipath + MMSE
```

## 多径输出

每个 Case 输出：

```text
BER vs Es/N0
FER vs Es/N0
trueSuccessRate
reportedSuccessRate
miscorrectionRate
decoderFailureRate
channelHardBER before equalization
equalizedHardBER after equalization
SNR@FER1e-1
SNR@FER1e-2
relative AWGN loss
avg equalization time
avg decoding time
```

注意均衡时延和 BCH 译码时延必须分开：

```text
equalizationTimeUs
decodeTimeUs
totalReceiverTimeUs
```

---

# 十二、频偏实验的两组接收端条件

频偏信道：

[
y[k]
====

x[k]
e^{j(2\pi\epsilon k+\phi_0)}
+
n[k]
]

建议用整帧累计相位旋转量控制频偏：

[
\Delta\phi_{\mathrm{frame}}
===========================

2\pi\epsilon(N-1)
]

这样不同码长下可以按“整帧累计旋转角”比较。

---

## 12.1 第一组：理想频偏补偿

接收端已知真实：

[
\epsilon,\phi_0
]

执行：

[
\tilde y[k]
===========

y[k]
e^{-j(2\pi\epsilon k+\phi_0)}
]

理论上补偿后应恢复为普通 AWGN：

[
\tilde y[k]\approx x[k]+n'[k]
]

这一组的目的不是作为最终性能结论，而是验证：

* CFO 注入正确；
* 相位方向正确；
* 复数噪声正确；
* 补偿公式正确；
* 补偿后结果与 AWGN 基线一致。

建议只做小规模验证，不做全部正式长跑。

Gate 应要求：

```text
perfect-compensation FER 与 AWGN 统计相容
hard-bit mismatch 在相同共享噪声条件下为 0 或符合严格预期
```

---

## 12.2 第二组：残余频偏，不补偿剩余频偏

你已经明确要求：

> 残余频偏实验中，不补偿剩余频偏。

因此正式主链路为：

```text
BPSK
→ 注入固定 residual CFO
→ 不做任何 residual CFO compensation
→ 直接取接收复信号实部硬判决
→ BCH decode
```

硬判决：

[
\hat c_k=
\begin{cases}
0,&\Re{y[k]}\ge0,\
1,&\Re{y[k]}<0.
\end{cases}
]

注意：

* 不做相位跟踪；
* 不做 PLL；
* 不做导频估计；
* 不做粗频偏估计；
* 不做剩余 CFO 补偿；
* 只研究 BCH 在固定残余旋转下的容忍度。

---

# 十三、频偏参数建议

使用整帧累计旋转角：

```text
0°
5°
10°
15°
20°
30°
45°
60°
75°
90°
120°
180°
```

其中：

* 0°：AWGN 等效基线；
* 5°～30°：轻度残余频偏；
* 45°～90°：明显性能恶化区；
* 120°～180°：极端失效区。

建议分两类实验。

## 13.1 固定 SNR 扫频偏

选取每个 Case 的三个参考 SNR：

```text
AWGN FER≈1e-1 对应点
AWGN FER≈1e-2 对应点
高 SNR 低误码点
```

扫描累计旋转角。

输出：

[
\mathrm{FER}\text{ vs }\Delta\phi
]

这直接反映频偏敏感性。

## 13.2 固定残余频偏扫 SNR

选一个中等频偏，例如：

[
\Delta\phi_{\mathrm{frame}}=30^\circ
]

再跑：

[
\mathrm{FER}\text{ vs }E_s/N_0
]

与 AWGN 曲线比较。

必要时再选：

[
60^\circ
]

作为重度频偏。

---

# 十四、频偏适应性如何统计

定义目标 FER：

[
F^\star=10^{-1}
]

或：

[
10^{-2}
]

最大容忍累计相位旋转：

[
\boxed{
\phi_{\max}(F^\star,\gamma)
===========================

\max{
\phi:\mathrm{FER}(\phi,\gamma)\le F^\star
}
}
]

也可以固定频偏，计算 SNR 损失：

[
\boxed{
L_{\mathrm{CFO}}(F^\star,\phi)
==============================

## \mathrm{SNR}_{\mathrm{CFO}}(F^\star,\phi)

\mathrm{SNR}_{\mathrm{AWGN}}(F^\star)
}
]

最终比较：

```text
哪个 Case 容忍的累计旋转最大
哪个 Case 误纠率增长最快
哪个 Case 在高 SNR 下仍因 CFO 出现 error floor
```

---

# 十五、短时遮挡实验规划

信道：

[
y[k]
====

a[k]x[k]+n[k]
]

其中：

[
a[k]=
\begin{cases}
A_{\mathrm{block}},&s\le k<s+L,\
1,&\text{其他}.
\end{cases}
]

## 衰减档位

建议：

```text
-6 dB
-12 dB
-20 dB
完全遮挡 A=0
```

幅度系数必须由功率 dB 转换：

[
\boxed{
A_{\mathrm{block}}
==================

10^{L_{\mathrm{dB}}/20}
}
]

例如：

[
-20\text{ dB}\Rightarrow A=0.1
]

不能使用：

[
10^{-20/10}=0.01
]

作为幅度，否则会重复平方。

## 遮挡长度

```text
1,2,4,8,12,15,16,20,30,32,48,64
```

特别保留 15、16、30、32，用于观察分块边界。

## 起点

```text
frame start
frame middle
frame end
segment interior
segment boundary
uniform random
```

每个随机起点至少 100 组。

---

# 十六、遮挡敏感性指标

## 固定 SNR

输出：

[
\mathrm{FER}(L,A)
]

[
\mathrm{miscorrectionRate}(L,A)
]

## 临界遮挡长度

[
\boxed{
L_{\max}(F^\star,A,\gamma)
==========================

\max{
L:\mathrm{FER}(L,A,\gamma)\le F^\star
}
}
]

## 位置敏感性

比较：

```text
相同长度遮挡落在分块内部
相同长度遮挡跨分块边界
相同长度遮挡落在整块码任意位置
```

S200/S300 可能对分块边界表现出明显差异。

---

# 十七、突发错误实验规划

突发错误主模型直接作用在硬判决 bit 上。

设编码码字为：

[
\boldsymbol c
]

连续翻转：

[
r_i=
\begin{cases}
1-c_i,&s\le i<s+L_b,\
c_i,&\text{其他}.
\end{cases}
]

## 17.1 纯突发错误

```text
不加 AWGN
只连续翻转 bit
```

目的：

> 直接测量码结构本身对连续错误的敏感性。

## 17.2 AWGN + 突发错误

选取一个固定背景 SNR：

建议使用各 Case AWGN 的 waterfall 中点，或统一符号 SNR。

然后：

```text
AWGN hard decision
→ 再连续翻转 Lb 个 bit
→ BCH decode
```

但需明确 burst 是在信道硬判决后注入的人为错误模型。

---

# 十八、突发长度和起点

长度：

```text
1,2,3,4,5,6,7,8,10,12,14,15,16,
20,24,29,30,31,32,48,64
```

关键点：

* S200/S300：15 bit 子块边界；
* B200：(t=6)；
* B300：(t=10)；
* B300-426：(t=14)。

起点：

```text
0
last possible
segment interior
just before segment boundary
exactly on segment boundary
uniform random
```

---

# 十九、突发错误敏感性如何统计

## 19.1 FER vs burst length

[
\boxed{
\mathrm{FER}_{\mathrm{burst}}(L_b)
==================================

\frac{
N_{\mathrm{payloadError}}(L_b)
}{
N_{\mathrm f}(L_b)
}
}
]

## 19.2 误纠率 vs burst length

[
\mathrm{miscorrectionRate}(L_b)
]

这对分块查表 BCH 尤其重要。

## 19.3 临界突发长度

设目标 FER：

[
F^\star
]

定义：

[
\boxed{
L_{b,\max}(F^\star)
===================

\max{
L_b:\mathrm{FER}(L_b)\le F^\star
}
}
]

建议同时统计：

```text
FER≤0.01
FER≤0.1
FER≤0.5
```

## 19.4 起点敏感性

定义：

[
\mathrm{FER}(s,L_b)
]

输出：

```text
平均 FER
最差起点 FER
最好起点 FER
起点标准差
```

对于分块码，这能显示 burst 是否跨块。

---

# 二十、正式实验规模

## Smoke

每种信道：

```text
每个 Case
少量代表参数
每点500帧
```

## Prescan

```text
每点2000帧
```

用于选关键区间。

## Formal

继续使用：

```text
minFrames = 5000
targetFrameErrors = 200
maxFrames = 50000
```

但对纯 burst 实验，建议固定帧数，而不是按错误数停止：

```text
每个 burst length / start 策略：
至少5000帧
```

原因是很多突发配置 FER 接近 0 或 1，固定帧数更容易公平比较。

---

# 二十一、正式输出图

所有图使用：

```text
Python matplotlib
PNG only
```

横轴涉及信噪比时，统一：

```text
符号信噪比 Es/N0（dB）
```

## 多径

```text
200bit_awgn_vs_multipath_fer.png
300bit_awgn_vs_multipath_fer.png
multipath_snr_loss_at_target_fer.png
multipath_miscorrection_comparison.png
```

## 频偏

```text
200bit_fer_vs_residual_phase_rotation.png
300bit_fer_vs_residual_phase_rotation.png
cfo_tolerance_at_target_fer.png
awgn_vs_residual_cfo_fer.png
cfo_miscorrection_rate.png
```

## 遮挡

```text
fer_vs_blockage_length.png
fer_vs_blockage_attenuation.png
blockage_position_sensitivity.png
blockage_miscorrection_rate.png
```

## Burst

```text
fer_vs_burst_length.png
miscorrection_vs_burst_length.png
burst_start_sensitivity.png
burst_critical_length.png
```

## 综合信道适应性

```text
channel_snr_loss_comparison.png
channel_critical_tolerance_comparison.png
channel_miscorrection_comparison.png
```

不要用雷达图替代正式数据，除非只是附加展示。

---

# 二十二、最终综合结论的组织方式

最终应按每个 payload 组分别回答：

## 200 bit

```text
S200 vs B200
```

比较：

* 多径损失；
* 残余频偏容忍度；
* 遮挡长度容忍度；
* burst 临界长度；
* 误纠率；
* 显式失败率。

## 300 bit

```text
S300 vs B300 vs B300-426
```

同样比较。

最后不能只说“某个码最好”，而应写成：

```text
AWGN下……
多径+MMSE下……
不补偿残余频偏下……
短时遮挡下……
连续突发错误下……
```

因为不同 BCH 结构可能在不同错误机制下各有优势。

---

# 二十三、更新后的关键 Gate

```text
PASS_BCH_S2_01_CHANNEL_CONTRACT
PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION
SKIPPED_BCH_S2_03_AWGN_RERUN
PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE
PASS_BCH_S2_05_RESIDUAL_CFO
PASS_BCH_S2_06_SHORT_BLOCKAGE
PASS_BCH_S2_07_BURST_SENSITIVITY
PASS_BCH_S2_08_CHANNEL_ADAPTATION_COMPARISON
PASS_BCH_S2_09_MATLAB_CHANNEL_REFERENCE
```

最终：

```text
PASS_BCH_S2_MULTI_CHANNEL_ADAPTATION
```

# 最终规划定位

你现在的 S2 主线应正式冻结为：

```text
复用 S1 AWGN 正式基线
→ 固定重度多径 h=[1,0.65,0.35]，单位能量归一化
→ 已知信道 MMSE 均衡
→ 理想频偏补偿链路验证
→ 残余频偏不补偿正式实验
→ 短时遮挡实验
→ 纯 burst 与 AWGN+burst
→ 统计 FER、误纠率、临界容忍参数
→ 计算相对 AWGN 的性能损失
→ 输出信道适应性综合表
```

其中老师要求的三个输出最终分别对应：

| 老师要求    | 正式统计方式                               |
| ------- | ------------------------------------ |
| 信道适应性   | 相对 AWGN 的 SNR 损失、固定条件 FER 放大量、临界容忍参数 |
| FER     | 最终 payload 帧错误数 / 总帧数                |
| 突发错误敏感性 | FER/误纠率随 burst 长度与起点变化、临界 burst 长度   |
