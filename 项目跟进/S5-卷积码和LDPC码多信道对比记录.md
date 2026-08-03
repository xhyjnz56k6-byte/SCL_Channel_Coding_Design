# S5 卷积码与 LDPC 码多信道对比实验记录

## 1. 项目概述

本项目对应信道编码方案设计任务中的 **S5 多信道综合对比实验**。

实验以 300 bit 高速电文为输入，在统一 BPSK 复基带链路下，对以下两组近似码率方案进行比较：

| 比较组 | 卷积码方案 | LDPC 方案 | 实际码率 |
|---|---|---|---:|
| 近 2/3 码率组 | CC R2/3 | LDPC N480 | CC：300/459；LDPC：300/480 |
| 近 1/2 码率组 | CC R1/2 | LDPC N640 | CC：300/612；LDPC：300/640 |

测试信道包括：

1. AWGN；
2. 固定多径；
3. 30°载波频偏；
4. 线性时变频偏；
5. 5%已知连续擦除；
6. 5%未知突发干扰，ISR=10 dB。

项目分为三个主要实验阶段：

| 阶段 | 主要任务 |
|---|---|
| Stage01～Stage09 | 方案冻结、复基带链路实现、公式审计、C++/MATLAB Smoke 验证 |
| Stage10 | 六信道 Formal 正式仿真 |
| Stage11 | 中文科研绘图、指标汇总、场景推荐 |
| Stage12 | 对卷积码在 5%已知连续擦除下 FER 接近 1 的现象进行独立验证 |

---

# 2. 实验目的

## 2.1 总体目的

本实验的总体目的是比较卷积码和 LDPC 码在不同信道条件下的：

- 误码率 BER；
- 误帧率 FER；
- 译码时延；
- LDPC 平均译码迭代次数；
- LDPC 达到最大迭代次数的帧比例；
- 相对 AWGN 的性能损失；
- 不同场景下的鲁棒性和适用性。

最终需要回答：

1. 在常规噪声和相位失真信道下，卷积码与 LDPC 码哪一种更可靠；
2. 在固定多径条件下，哪一种编码方案性能损失更小；
3. 在局部连续损伤条件下，哪一种编码方案更稳定；
4. 可靠性、译码复杂度和时延之间如何权衡；
5. 不同码率和信道条件下应选择哪一种编码方案。

## 2.2 Stage12 的附加目的

Stage10 结果显示：

- CC R2/3 在 5%已知连续擦除条件下，FER 接近 1；
- CC R1/2 在相同条件下也存在严重 FER 平台。

Stage12 用于判断该现象究竟是：

- 卷积码对未交织连续擦除的真实敏感性；
- 还是擦除位置、打孔、去打孔、LLR 或 Viterbi 译码实现错误。

---

# 3. 基础通信链路

## 3.1 完整实验流程

```text
300 bit随机payload
→ 信道编码
→ BPSK调制
→ 信道损伤
→ AWGN
→ 信道补偿或软信息计算
→ 软判决译码
→ 恢复300 bit payload
→ 统计BER、FER、时延和迭代次数
```

## 3.2 BPSK 映射

比特映射规则为：

$$
x_k =
\begin{cases}
+1, & b_k=0 \
-1, & b_k=1
\end{cases}
$$

在复基带实现中：

$$
x_k\in{+1+j0,,-1+j0}
$$

## 3.3 符号信噪比与噪声方差

Formal 实验横轴统一使用符号信噪比：

$$
\frac{E_s}{N_0}
$$

线性信噪比为：

$$
\gamma_s=10^{\frac{E_s/N_0\left(\mathrm{dB}\right)}{10}}
$$

实部或虚部高斯噪声方差为：

$$
\sigma^2=\frac{1}{2\gamma_s}
$$

即：

$$
\sigma^2=
\frac{1}
{2\cdot 10^{\frac{E_s/N_0\left(\mathrm{dB}\right)}{10}}}
$$

AWGN 模型为：

$$
y_k=x_k+n_k
$$

其中：

$$
n_k\sim\mathcal{N}(0,\sigma^2)
$$

BPSK 的对数似然比为：

$$
L_k=\ln
\frac{P(b_k=0\mid y_k)}
{P(b_k=1\mid y_k)}
$$

在实 BPSK AWGN 条件下：

$$
L_k=\frac{2y_k}{\sigma^2}
$$

码率统一定义为：

$$
R=
\frac{\text{原始输入长度}}
{\text{实际发送编码长度}}
$$

符号信噪比与比特信噪比满足：

$$
\frac{E_b}{N_0}\left(\mathrm{dB}\right)
=
\frac{E_s}{N_0}\left(\mathrm{dB}\right)

10\log_{10}R
$$

---

# 4. 编码方案参数

## 4.1 卷积码参数

| 参数         | 数值             |
| ---------- | -------------- |
| payload 长度 | 300 bit        |
| 约束长度       | 7              |
| 生成多项式      | 171/133，八进制    |
| 尾比特        | 6 个零尾比特        |
| 母码率        | 1/2            |
| 译码方式       | 完整块软判决 Viterbi |
| 软信息精度      | Float          |
| 终止方式       | 终止到零状态         |

卷积码编码输入总长度为：

$$
K_{\mathrm{CC}}=300+6=306
$$

### CC R1/2

母码输出长度为：

$$
N_{\mathrm{R1/2}}=2\times306=612
$$

实际码率为：

$$
R_{\mathrm{CC,R1/2}}
=\frac{300}{612}
\approx0.4902
$$

### CC R2/3

采用打孔模式：

``` text
1101
```

即每 4 个母码比特保留 3 个。

实际发送长度为：

$$
N_{\mathrm{R2/3}}=459
$$

实际码率为：

$$
R_{\mathrm{CC,R2/3}}
=\frac{300}{459}
\approx0.6536
$$

## 4.2 LDPC 参数

本次 LDPC 直接使用裁剪后的 5G NR BG2 QC-LDPC，不包含速率匹配和速率恢复。

| 方案        | 输入长度 | 发送长度 |    实际码率 | 译码方法 | 最大迭代次数 |
| --------- | ---: | ---: | ------: | ---- | -----: |
| LDPC N480 |  300 |  480 |  0.6250 | NMS  |     32 |
| LDPC N640 |  300 |  640 | 0.46875 | NMS  |     32 |

NMS 更新可表示为：

$$
L_{c\rightarrow v}
=
\alpha
\left(
\prod_{v'\in\mathcal{N}(c)\setminus v}
\operatorname{sgn}
\left(
L_{v'\rightarrow c}
\right)
\right)
\min_{v'\in\mathcal{N}(c)\setminus v}
\left|
L_{v'\rightarrow c}
\right|
$$

其中：

* N480 的归一化系数为 0.95；
* N640 的归一化系数为 0.80。

S5 只使用 S4 中冻结的 NMS 工程方案，不重新比较 BP 和 NMS。BP 与 NMS 的算法对比属于后续 S6 任务。

---

# 5. 信道模型与冻结参数

## 5.1 AWGN

模型：

$$
y_k=x_k+n_k
$$

用途：

* 作为无附加信道损伤的基准；
* 检查 S5 复基带链路是否与 S3、S4 原 AWGN 结果一致；
* 计算其他信道相对 AWGN 的性能损失。

## 5.2 固定多径

多径模型：

$$
r_k=
\sum_{\ell=0}^{L-1}
h_\ell x_{k-d_\ell}
+n_k
$$

其中：

* $h_\ell$ 为第 $\ell$ 条路径的增益；
* $d_\ell$ 为对应的整数符号时延；
* 信道参数在每帧内保持固定；
* 接收端采用已知信道条件下的 MMSE 均衡。

MMSE 均衡的基本形式为：

$$
\hat{X}(f)=
\frac{H^*(f)}
{|H(f)|^2+\sigma^2}
Y(f)
$$

用途：

* 测试码在码间干扰条件下的稳定性；
* 比较两种编码方案对均衡残余误差的敏感程度。

## 5.3 30°载波频偏

本实验使用受控的 30°相位旋转模型：

$$
r_k=x_ke^{j\theta}+n_k
$$

其中：

$$
\theta=30^\circ=\frac{\pi}{6}
$$

该模型用于复现 BCH S2 中采用的 30°载波偏移条件。

用途：

* 测试接收软信息在固定相位旋转下的可靠性；
* 比较 CC 与 LDPC 对残余载波偏差的敏感程度。

## 5.4 线性时变频偏

模型为：

$$
r_k=x_ke^{j\phi_k}+n_k
$$

相位满足：

$$
\phi_k=
\phi_0
+
2\pi
\sum_{i=0}^{k}
\varepsilon_i
$$

频偏随符号序号线性变化：

$$
\varepsilon_k=
\varepsilon_0+\beta k
$$

该模型仅表示单径线性时变频偏，不代表完整真实卫星多普勒信道。

用途：

* 测试编码方案对随时间累积相位误差的鲁棒性；
* 区分固定 CFO 与时变频偏造成的性能差异。

## 5.5 5%已知连续擦除

发送长度为 $N$ 时，擦除长度为：

$$
L_{\mathrm{erase}}
=\operatorname{round}(0.05N)
$$

擦除区间为：

$$
\mathcal{E}
=
\left{
s,s+1,\ldots,s+L_{\mathrm{erase}}-1
\right}
$$

对于已知擦除位置：

$$
L_k=0,\qquad k\in\mathcal{E}
$$

其余符号正常计算 LLR。

不同方案的擦除长度约为：

| 方案        | 发送长度 | 5%擦除长度 |
| --------- | ---: | -----: |
| CC R2/3   |  459 |     23 |
| LDPC N480 |  480 |     24 |
| CC R1/2   |  612 |     31 |
| LDPC N640 |  640 |     32 |

该模型用于近似短时遮挡造成的完全失真区，但不等同于完整物理遮挡衰落模型。

## 5.6 5%未知突发干扰

突发区长度为：

$$
L_{\mathrm{burst}}
==================

\operatorname{round}(0.05N)
$$

干扰信号功率与有效信号功率之比为：

$$
\mathrm{ISR}=10\ \mathrm{dB}
$$

线性功率比为：

$$
\gamma_I=
10^{\frac{10}{10}}=10
$$

突发干扰区接收信号可表示为：

$$
r_k=x_k+i_k+n_k
$$

其中：

$$
E\left[|i_k|^2\right]
=====================

10E\left[|x_k|^2\right]
$$

接收端不知道突发干扰位置，因此仍按普通接收符号计算 LLR。

用途：

* 测试编码方案对未知强干扰的适应性；
* 观察高信噪比下是否存在由局部损伤产生的误码平台。

---

# 6. Formal 实验参数

| 参数         | 数值       |
| ---------- | -------- |
| Es/N0 范围   | -5～10 dB |
| 步长         | 0.5 dB   |
| 每条曲线点数     | 31       |
| 最小帧数       | 1000     |
| 目标帧错误数     | 200      |
| 最大帧数       | 50000    |
| payload 长度 | 300 bit  |
| 信道数量       | 6        |
| 比较组数量      | 2        |
| 每组编码方案数    | 2        |

单方案点总数为：

$$
N_{\mathrm{point}}
=2\times6\times31\times2

744
$$

停止规则为：

```text
至少运行1000帧；
若累计帧错误数达到200，则结束该点；
否则最多运行50000帧。
```

BER 为：

$$
\mathrm{BER}
=\frac{N_{\mathrm{bit,error}}}
{300N_{\mathrm{frame}}}
$$

FER 为：

$$
\mathrm{FER}
=
\frac{N_{\mathrm{frame,error}}}
{N_{\mathrm{frame}}}
$$

其中一帧只要存在至少一个 payload bit 错误，即记为帧错误。

---

# 7. 实验方法

## 7.1 Smoke 与公式审计

Smoke 阶段完成以下检查：

1. C++ 与 MATLAB 使用相同固定 payload；
2. C++ 与 MATLAB 分别独立编码；
3. 比较卷积码母码序列；
4. 比较 R2/3 打孔后 459 个发送位；
5. 比较无噪声译码后的 300 bit payload；
6. 对 BPSK、噪声方差、LLR、CFO、多径和擦除公式逐项审计；
7. 检查 NaN、Inf、长度错误和比特映射错误；
8. 检查 C++ 与 MATLAB 官方卷积码链路逐 bit 一致。

LDPC 未与 MATLAB 官方 5G NR 函数逐 bit 对比，原因是本项目直接裁剪 BG2，不包含标准速率匹配和速率恢复，链路结构与 MATLAB 官方 NR LDPC 流程不完全一致。

## 7.2 Formal 仿真

Formal 采用四个并行 shard 执行，每个任务固定：

* 编码方案；
* 信道类型；
* Es/N0；
* 公共 payload 帧编号；
* 公共噪声池；
* 信道状态种子；
* 停止条件。

每个任务输出：

```text
final_result.csv
timing_samples.csv
checkpoint.json
run.log
task_manifest.json
```

所有任务完成后合并为：

```text
results/formal/merged/formal_merged_results.csv
```

合并结果共 744 行。

## 7.3 Stage11 绘图

Stage11 不重新运行编译码链路，只读取 Formal 合并 CSV。

绘图规则：

* BER、FER 使用对数纵轴；
* 时延和迭代次数使用线性纵轴；
* 不平滑；
* 不拟合；
* 不外推；
* 不补造数据点；
* 观测零错误点在 CSV 中保留为 0；
* 对数坐标图中不绘制 0；
* 不使用人为 error floor；
* 每张图保存图像、绘图数据、manifest、检查报告和 SHA-256。

## 7.4 Stage12 独立验证

Stage12 仅验证连续擦除问题，不重新运行六信道 Formal。

### 擦除比例扫描

CC R2/3 测试：

| 擦除比例 | Es/N0       |
| ---: | ----------- |
|   0% | 0、4、8、10 dB |
|   1% | 0、4、8、10 dB |
|   2% | 0、4、8、10 dB |
|   3% | 0、4、8、10 dB |
|   5% | 0、4、8、10 dB |

### 单帧 Trace

固定选择 frame 0 和 frame 1，导出：

* payload；
* 编码器尾比特输入；
* 母码；
* 打孔发送位；
* BPSK 符号；
* 擦除 mask；
* 擦除前后符号；
* 接收符号；
* LLR；
* 去打孔软信息；
* Viterbi 状态路径；
* 译码 payload；
* bit error mask。

### MATLAB 官方链路

MATLAB 使用：

```matlab
poly2trellis
convenc
vitdec
```

固定向量只共享原始 payload。

统计实验独立产生：

* payload；
* AWGN；
* 擦除位置；
* 编码结果；
* 译码结果。

### 交织诊断

CC R2/3 的 459 个发送符号采用：

$$
17\times27=459
$$

块交织方式：

```text
发送端：按行写入，按列读出；
接收端：按列写入，按行读出。
```

交织仅作为诊断，不进入 S5 正式方案推荐。

---

# 8. 主要优化与修复

## 8.1 统一复基带信道核心

原有实 BPSK 链路不能严谨描述 CFO 和时变频偏。

S5 将信道核心统一为复基带形式，并将每种信道损伤独立实现，避免不同信道模型相互耦合。

主要信道函数包括：

```text
applyAwgn
applyMultipath
applyCarrierFrequencyOffset
applyLinearTimeVaryingFrequency
applyKnownBlockage
applyUnknownBurstInterference
equalizeMultipath
computeComplexBpskLlr
```

## 8.2 公共帧池与噪声池

C++ Smoke 使用公共帧池和公共噪声池，保证：

* 不同编码方案比较时使用相同 payload；
* 相同信道和 SNR 下使用同源噪声；
* 不同算法之间的随机条件公平；
* 仿真可以断点恢复和复现。

## 8.3 Formal 与绘图分离

将正式仿真和绘图分为两个阶段：

```text
Stage10：生成可信原始统计
Stage11：读取统计结果并绘图
```

这样避免并行仿真过程中使用不完整数据绘图，也保证所有图都来自同一份冻结 Formal CSV。

## 8.4 中文科研绘图

原 86 张英文图已归档，重新生成中文图。

统一使用：

* 中文标题；
* 中文横纵轴；
* 简洁图例；
* Microsoft YaHei 字体；
* 颜色区分编码方案；
* 线型和标记区分信道。

## 8.5 Aggregate 汇总图

新增 20 张多曲线汇总图，包括：

### 可靠性汇总图

1. 近2/3码率组常规信道 FER；
2. 近2/3码率组局部连续损伤 FER；
3. 近1/2码率组常规信道 FER；
4. 近1/2码率组局部连续损伤 FER；
5. 近2/3码率组常规信道 BER；
6. 近2/3码率组局部连续损伤 BER；
7. 近1/2码率组常规信道 BER；
8. 近1/2码率组局部连续损伤 BER。

### 时延汇总图

9. 近2/3组六信道平均译码时延；
10. 近1/2组六信道平均译码时延；
11. 近2/3组六信道最大译码时延；
12. 近1/2组六信道最大译码时延。

### 单方案附录图

13. CC R2/3 六信道 FER；
14. LDPC N480 六信道 FER；
15. CC R1/2 六信道 FER；
16. LDPC N640 六信道 FER；
17. N480 六信道平均迭代次数；
18. N640 六信道平均迭代次数；
19. N480 六信道最大迭代帧比例；
20. N640 六信道最大迭代帧比例。

## 8.6 连续擦除独立验证

通过 C++ 和 MATLAB 两条独立链路复现 CC 的严重 FER 平台，排除了以下错误：

* 擦除位置作用到错误序列；
* R2/3 打孔相位错误；
* 去打孔掩码错误；
* BPSK 符号方向错误；
* LLR 符号错误；
* 已知擦除 LLR 未设为 0；
* Viterbi 终止状态错误；
* BER、FER 整数统计错误。

---

# 9. Formal 实验结果

## 9.1 实验规模

| 指标               |         结果 |
| ---------------- | ---------: |
| paired task 数量   |        372 |
| Formal 方案点       |        744 |
| paired frame 数量  |  8,115,263 |
| scheme decode 次数 | 16,230,526 |
| checkpoint 完成数   |    372/372 |
| NaN/Inf          |          0 |
| Stage11 原始中文图    |         86 |
| Aggregate 汇总图    |         20 |

Formal 合并结果 SHA-256：

```text
dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947
```

## 9.2 近 2/3 码率组结果

比较：

```text
CC R2/3，N=459，R≈0.6536
LDPC N480，R=0.625
```

### 常规信道结论

从 AWGN、固定多径、30°载波频偏和线性时变频偏结果看：

* CC R2/3 的 FER waterfall 普遍比 LDPC N480 更靠左；
* 在相同 Es/N0 下，CC R2/3 的 BER 和 FER 通常更低；
* 固定多径是两种方案中性能损失较大的常规信道；
* N480 的译码时延在高 SNR 下明显低于 CC R2/3；
* N480 在低 SNR 下迭代次数接近最大值，时延明显增加。

本项目中的 N480 并不是标准 5G NR 完整速率匹配码，而是直接裁剪后的短 BG2 结构。短码长、裁剪结构、直接发送方式和冻结 NMS 参数共同限制了其性能。

### 局部损伤结论

5%已知连续擦除下：

* CC R2/3 的 FER 接近 1；
* LDPC N480 随 Es/N0 增大进入明显 waterfall；
* 在该场景中，LDPC N480 明显优于 CC R2/3。

5%未知突发干扰下：

* 两种方案均存在严重 FER 平台；
* CC R2/3 的 FER 约在 0.95 附近；
* LDPC N480 的 FER 约在 0.97 附近；
* 两者均未达到高可靠目标。

## 9.3 近 1/2 码率组结果

比较：

```text
CC R1/2，N=612，R≈0.4902
LDPC N640，R=0.46875
```

### 常规信道结论

* LDPC N640 在 AWGN、CFO、线性时变频偏和固定多径下整体优于 CC R1/2；
* N640 的 waterfall 通常更靠左；
* 固定多径对 CC R1/2 的影响明显大于对 LDPC N640 的影响；
* CC R1/2 的译码时延相对稳定；
* N640 在高 SNR 下平均迭代次数接近 1，译码时延明显下降。

### 局部损伤结论

5%已知连续擦除下：

* CC R1/2 的 FER 接近 1；
* LDPC N640 的 FER 随 Es/N0 快速下降；
* LDPC N640 对已知连续擦除具有明显优势。

5%未知突发干扰下：

* CC R1/2 的 FER 维持在约 0.8～0.9；
* LDPC N640 的 FER 高 SNR 平台约为 0.06；
* N640 明显优于 CC R1/2；
* 但 N640 仍未达到 FER=0.01 的高可靠目标。

---

# 10. Stage12 连续擦除验证结果

## 10.1 C++ 统计结果

CC R2/3 在 5%已知连续擦除下：

| Es/N0 | 处理帧数 | 帧错误数 |   FER |
| ----: | ---: | ---: | ----: |
|  4 dB | 1000 |  998 | 0.998 |
|  8 dB | 1000 |  998 | 0.998 |
| 10 dB | 1000 |  998 | 0.998 |

CC R1/2 的补充结果：

| 条件           |   FER |
| ------------ | ----: |
| 5%连续擦除，高 SNR | 0.999 |

## 10.2 MATLAB 官方链路结果

CC R2/3 在 5%已知连续擦除下：

| Es/N0 | MATLAB FER |
| ----: | ---------: |
|  4 dB |      0.999 |
|  8 dB |      0.999 |
| 10 dB |      1.000 |

C++ 与 MATLAB 的 95% Wilson 置信区间重叠，说明两条独立实现复现了相同的严重 FER 平台。

## 10.3 单帧 Trace 结果

|     帧编号 | 擦除起点 | 擦除长度 | payload 错误数 |  错误跨度 |
| ------: | ---: | ---: | ----------: | ----: |
| frame 0 |   92 |   23 |       5 bit | 8 bit |
| frame 1 |  282 |   23 |       8 bit | 9 bit |

结论：

* 连续擦除没有使 300 bit 全部随机错误；
* 错误集中在擦除对应的局部 payload 区域；
* 每帧通常只有少量连续 bit 错误；
* 但 FER 定义为一帧中只要有一个 bit 错误即判错；
* 因而少量局部错误足以使 FER 接近 1。

## 10.4 交织诊断结果

采用 17×27 块交织后：

| Es/N0 | 无交织 FER | 交织帧数 | 交织帧错误数 |
| ----: | ------: | ---: | -----: |
|  4 dB |   0.998 | 5000 |      0 |
|  8 dB |   0.998 | 5000 |      0 |
| 10 dB |   0.998 | 5000 |      0 |

结论：

* 卷积码并不是无法纠正相同数量的错误；
* 主要问题是错误连续集中；
* 交织将连续擦除分散后，Viterbi 可以利用未擦除的相邻约束恢复路径；
* 该实验仅用于机理诊断，不属于 S5 正式方案，不代替 S7 的交织实验。

---

# 11. 鲁棒性分析

本项目不构造单一的“鲁棒性分数”。

鲁棒性通过以下指标综合判断：

1. 是否覆盖目标 FER；
2. 达到 FER=0.1 所需的 Es/N0；
3. 达到 FER=0.01 所需的 Es/N0；
4. 相对自身 AWGN 的信道损失；
5. 高 SNR 下是否出现性能平台；
6. 平均和 P95 译码时延；
7. 最大观测时延；
8. LDPC 平均迭代次数；
9. LDPC 达到最大迭代次数的帧比例。

目标 FER 所需信噪比通过相邻两个非零实测点进行对数域插值：

$$
x_t
===

x_1
+
\frac{
\log_{10}F_t-\log_{10}F_1
}{
\log_{10}F_2-\log_{10}F_1
}
\left(
x_2-x_1
\right)
$$

其中：

* $F_t$ 为目标 FER；
* $(x_1,F_1)$ 和 $(x_2,F_2)$ 为包围目标值的相邻实测点。

信道损失定义为：

$$
\Delta_{\mathrm{channel}}
=
\left.
\frac{E_s}{N_0}
\right|_{\mathrm{channel},F_t}
-
\left.
\frac{E_s}{N_0}
\right|_{\mathrm{AWGN},F_t}
$$

若曲线没有覆盖目标 FER，则不外推，也不伪造目标信噪比。

---

# 12. 场景选择结论

| 场景       | 近2/3码率组推荐 | 近1/2码率组推荐 | 主要依据                        |
| -------- | --------- | --------- | --------------------------- |
| AWGN     | CC R2/3   | LDPC N640 | 近2/3组 CC 更可靠；近1/2组 N640 更可靠 |
| 固定多径     | CC R2/3   | LDPC N640 | CC R2/3优于N480；N640优于CC R1/2 |
| 30°载波频偏  | CC R2/3   | LDPC N640 | waterfall位置和目标FER覆盖         |
| 线性时变频偏   | CC R2/3   | LDPC N640 | 相同码率组下的实测FER                |
| 5%已知连续擦除 | LDPC N480 | LDPC N640 | CC出现FER接近1的平台               |
| 5%未知突发干扰 | 无高可靠方案    | LDPC N640 | N640平台最低，但仍未覆盖FER=0.01      |

总体结论：

1. **近2/3码率组**：常规信道优先选择 CC R2/3；
2. **近1/2码率组**：常规信道优先选择 LDPC N640；
3. **已知连续擦除**：LDPC 明显优于未交织卷积码；
4. **未知强突发干扰**：N640 相对最好，但仍存在误码平台；
5. **高 SNR 低时延**：LDPC 可通过提前停止获得较低平均译码时延；
6. **时延稳定性**：CC 译码时延随 SNR 变化较小；
7. **最大译码时延**：受 Windows 调度尖峰影响，只作为最坏观测值，不单独用于方案推荐。

---

# 13. 结果图

## 13.1 核心可靠性汇总图

### 近2/3码率组常规信道 FER

```markdown
![近2/3码率组常规信道误帧率汇总](results/Aggregate/01_rate_near_2_3_regular_fer/figure.png)
```

### 近2/3码率组局部连续损伤 FER

```markdown
![近2/3码率组局部连续损伤误帧率汇总](results/Aggregate/02_rate_near_2_3_local_damage_fer/figure.png)
```

### 近1/2码率组常规信道 FER

```markdown
![近1/2码率组常规信道误帧率汇总](results/Aggregate/03_rate_near_1_2_regular_fer/figure.png)
```

### 近1/2码率组局部连续损伤 FER

```markdown
![近1/2码率组局部连续损伤误帧率汇总](results/Aggregate/04_rate_near_1_2_local_damage_fer/figure.png)
```

## 13.2 BER 汇总图

```markdown
![近2/3码率组常规信道误码率汇总](results/Aggregate/05_rate_near_2_3_regular_ber/figure.png)

![近2/3码率组局部连续损伤误码率汇总](results/Aggregate/06_rate_near_2_3_local_damage_ber/figure.png)

![近1/2码率组常规信道误码率汇总](results/Aggregate/07_rate_near_1_2_regular_ber/figure.png)

![近1/2码率组局部连续损伤误码率汇总](results/Aggregate/08_rate_near_1_2_local_damage_ber/figure.png)
```

## 13.3 时延汇总图

```markdown
![近2/3码率组六信道平均译码时延](results/Aggregate/09_rate_near_2_3_avg_decode_latency/figure.png)

![近1/2码率组六信道平均译码时延](results/Aggregate/10_rate_near_1_2_avg_decode_latency/figure.png)

![近2/3码率组六信道最大译码时延](results/Aggregate/11_rate_near_2_3_max_decode_latency/figure.png)

![近1/2码率组六信道最大译码时延](results/Aggregate/12_rate_near_1_2_max_decode_latency/figure.png)
```

## 13.4 单方案附录图

```markdown
![卷积码R2/3六信道FER](results/Aggregate/13_cc_r23_all_channels_fer/figure.png)

![LDPC N480六信道FER](results/Aggregate/14_ldpc_n480_all_channels_fer/figure.png)

![卷积码R1/2六信道FER](results/Aggregate/15_cc_r12_all_channels_fer/figure.png)

![LDPC N640六信道FER](results/Aggregate/16_ldpc_n640_all_channels_fer/figure.png)

![LDPC N480六信道平均迭代次数](results/Aggregate/17_ldpc_n480_avg_iterations/figure.png)

![LDPC N640六信道平均迭代次数](results/Aggregate/18_ldpc_n640_avg_iterations/figure.png)

![LDPC N480六信道最大迭代帧比例](results/Aggregate/19_ldpc_n480_max_iteration_rate/figure.png)

![LDPC N640六信道最大迭代帧比例](results/Aggregate/20_ldpc_n640_max_iteration_rate/figure.png)
```

---

# 14. 代码与结果存储位置

项目根目录：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design
```

S5 根目录：

```text
Task/Comparison/S5/
```

## 14.1 核心 C++ 代码

| 内容                 | 位置                                                        |
| ------------------ | --------------------------------------------------------- |
| S5 公共接口            | `Task/Comparison/S5/current/include/s5_comparison/s5.hpp` |
| 信道、LLR、编解码核心       | `Task/Comparison/S5/current/src/s5.cpp`                   |
| Formal 和 Trace 执行器 | `Task/Comparison/S5/current/src/s5_runner.cpp`            |
| CMake 构建入口         | `Task/Comparison/S5/CMakeLists.txt`                       |
| 单元测试               | `Task/Comparison/S5/current/tests/test_s5.cpp`            |

## 14.2 Formal 脚本

| 内容               | 位置                                                        |
| ---------------- | --------------------------------------------------------- |
| Formal 调度        | `Task/Comparison/S5/current/scripts/run_s5_formal.py`     |
| Formal 分片合并      | `Task/Comparison/S5/current/scripts/merge_grid_shards.py` |
| Formal 结果检查      | `Task/Comparison/S5/current/scripts/check_s5_results.py`  |
| Formal readiness | `Task/Comparison/S5/current/scripts/run_s5_readiness.py`  |
| 最终集成检查           | `Task/Comparison/S5/current/scripts/finalize_s5.py`       |

## 14.3 Stage11 绘图脚本

| 内容               | 位置                                                                    |
| ---------------- | --------------------------------------------------------------------- |
| 86 张中文图与推荐表      | `Task/Comparison/S5/current/scripts/stage11_analysis.py`              |
| 旧图归档             | `Task/Comparison/S5/current/scripts/archive_stage11_before_replot.py` |
| 20 张 Aggregate 图 | `Task/Comparison/S5/current/scripts/stage12_aggregate_plots.py`       |
| Stage12/重绘最终审计   | `Task/Comparison/S5/current/scripts/finalize_stage12_replot.py`       |

## 14.4 Stage12 验证代码

| 内容              | 位置                                                                                                  |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Stage12 C++ 验证器 | `Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/cpp/src/stage12_cc_validation.cpp`   |
| MATLAB 官方验证     | `Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/matlab/scripts/run_stage12_matlab.m` |
| Stage12 Gate    | `Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/scripts/check_stage12.py`            |
| Stage12 参数审计    | `Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/stage12_parameter_audit.md`          |
| Stage12 结论      | `Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/comparison/conclusion.md`            |

## 14.5 Formal 结果

| 内容            | 位置                                                                   |
| ------------- | -------------------------------------------------------------------- |
| Formal 完整任务结果 | `Task/Comparison/S5/results/formal/`                                 |
| Formal 合并结果   | `Task/Comparison/S5/results/formal/merged/formal_merged_results.csv` |
| Formal 合并审计   | `Task/Comparison/S5/results/formal/merged/formal_merge_audit.json`   |
| Formal Gate   | `Task/Comparison/S5/results/formal/merged/formal_gate.txt`           |

## 14.6 Stage11 结果

| 内容      | 位置                                                                                             |
| ------- | ---------------------------------------------------------------------------------------------- |
| 86 张中文图 | `Task/Comparison/S5/results/stage11/plots/`                                                    |
| 信道损失表   | `Task/Comparison/S5/results/stage11/s5_channel_loss_table.csv`                                 |
| 鲁棒性汇总   | `Task/Comparison/S5/results/stage11/s5_robustness_summary.csv`                                 |
| 时延汇总    | `Task/Comparison/S5/results/stage11/s5_latency_comparison.csv`                                 |
| 场景推荐表   | `Task/Comparison/S5/results/stage11/s5_scenario_recommendation.csv`                            |
| 原英文图归档  | `Task/Comparison/S5/results/stage11/archive/v01_20260803_before_chinese_replot_and_aggregate/` |

## 14.7 Aggregate 结果

```text
Task/Comparison/S5/results/Aggregate/
```

每一幅图的目录中包含：

```text
figure.png
figure_data.csv
plot_manifest.json
plot_check.md
说明.txt
sha256.txt
```

## 14.8 Stage12 结果

| 内容            | 位置                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------- |
| C++ 擦除比例扫描    | `stages/stage12_known_erasure_cc_validation/cpp/results/cpp_erasure_fraction_summary.csv`   |
| C++/MATLAB 对比 | `stages/stage12_known_erasure_cc_validation/comparison/cpp_matlab_summary.csv`              |
| Trace 汇总      | `stages/stage12_known_erasure_cc_validation/comparison/trace_summary.csv`                   |
| 交织诊断          | `stages/stage12_known_erasure_cc_validation/cpp/results/interleaver_diagnostic_summary.csv` |
| 单帧完整 Trace    | `stages/stage12_known_erasure_cc_validation/cpp/traces/`                                    |
| Stage12 Gate  | `stages/stage12_known_erasure_cc_validation/cpp/results/cpp_erasure_fraction_gate.json`     |

---

# 15. Gate 与项目状态

已通过的主要 Gate：

```text
PASS_S5_SMOKE
PASS_S5_FORMAL_READINESS
PASS_S5_FORMAL
PASS_S5_PLOT_AUDIT
PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION
PASS_S5_STAGE11_CHINESE_REPLOT
PASS_S5_AGGREGATE_PLOT_AUDIT
PASS_S5_STAGE11_STAGE12_FINAL_INTEGRATION
```

当前分支：

```text
S5-Compare
```

Stage12 和中文重绘提交：

```text
986144d1e591d910192240a77e85c9b8a53fd5ed
```

当前状态：

```text
S5实验、Stage12验证和中文绘图已经完成；
尚未合并到main。
```

---

# 16. 已知限制

1. LDPC 使用的是直接裁剪 BG2 结构，不是完整 5G NR 速率匹配链路；
2. 多径信道采用受控固定路径和已知信道 MMSE 均衡；
3. 30°载波频偏为受控相位偏移模型；
4. 线性时变频偏不是完整真实卫星多普勒模型；
5. 5%已知连续擦除只是短时完全失真区的近似模型；
6. 未知突发干扰只测试了 5%长度和 ISR=10 dB；
7. Stage12 交织实验只是诊断，不属于 S5 正式推荐；
8. 软件时延只适用于当前 Windows Release 环境；
9. 最大译码时延容易受到操作系统调度和后台任务影响；
10. 零错误点只能说明在有限帧数中未观测到错误，不能证明真实 BER 或 FER 为零；
11. 所有结论仅适用于当前 payload 长度、码长、码率、译码参数和受控信道模型。

---

# 17. 最终总结

本次 S5 实验完成了卷积码与 LDPC 码在六种信道条件下的统一对比。

主要结论如下：

1. 近2/3码率组中，CC R2/3 在四种常规信道下整体优于 LDPC N480；
2. 近1/2码率组中，LDPC N640 在四种常规信道下整体优于 CC R1/2；
3. 固定多径对高码率方案影响明显，尤其是 LDPC N480；
4. 未交织卷积码对连续集中擦除非常敏感；
5. LDPC 对已知连续擦除的恢复能力明显优于卷积码；
6. 未知强突发干扰会使所有方案出现高 SNR 性能平台；
7. LDPC 高 SNR 下可通过提前停止获得较低平均译码时延；
8. CC 的译码时延随 SNR 变化较小；
9. Stage12 的 C++ 和 MATLAB 独立实验确认了 CC 在 5%已知连续擦除下 FER 接近 1 的结果是真实现象，而不是实现错误；
10. 17×27 交织诊断证明连续损伤的集中性是卷积码失效的重要原因。

---
