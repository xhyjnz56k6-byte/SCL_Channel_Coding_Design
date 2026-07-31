<h1 align="center">

卷积码任务进度：S4

</h1>

# S4：300 bit 高速电文 5G NR LDPC 设计与仿真实验记录

## 1. 实验目的

本实验面向 300 bit 高速电文，研究 5G NR LDPC 短码的码长适配、BP/NMS 译码性能及工程实现代价，主要完成以下任务：

1. 构建不包含速率匹配和速率恢复的 Direct LDPC 编译码链路；
2. 对比 480 bit、576 bit 附近以及不超过 640 bit 的整块 LDPC 方案；
3. 对比 Layered BP 与 Layered NMS 的 BER、FER、迭代次数、译码时延和计算复杂度；
4. 为每个码长选择适合的 NMS 归一化因子；
5. 计算不同码长方案之间的相对编码增益；
6. 为后续 S5 中卷积码与 LDPC 的不同信道对比提供统一接口和正式基线。

老师文档中将 LDPC 定位为高速电文场景下卷积码的替换和性能对比方案，要求使用 300 bit 整块输入，对比 480、576 及不超过 640 bit 的短码，并输出编码增益、FER和平均/最大译码时延。:contentReference[oaicite:0]{index=0}

---

## 2. 实验链路

本实验采用 Direct LDPC 链路：

300 bit随机信息
→ BG2参数与提升因子选择
→ filler填充
→ Direct GF(2)系统编码
→ H·c^T=0校验
→ BPSK调制
→ AWGN信道
→ LLR计算
→ Layered BP或Layered NMS译码
→ syndrome提前停止
→ 提取300 bit原始信息
→ 统计BER、FER、迭代次数、时延与复杂度

本实验明确不包含：

* rateMatch；
* rateRecover；
* 循环缓冲；
* HARQ；
* LDPC分块；
* 交织。

码率统一定义为：

$$
R=\frac{\text{原始输入长度}}{\text{编码后实际发送长度}}
$$

BPSK映射为：

$$
0\rightarrow +1,\qquad 1\rightarrow -1
$$

符号信噪比采用：

$$
\mathrm{SNR}=\frac{E_s}{N_0}
$$

噪声方差为：

$$
\sigma^2=\frac{1}{2\cdot 10^{\mathrm{SNR}_{\mathrm{dB}}/10}}
$$

接收符号的初始LLR为：

$$
L_i=\frac{2y_i}{\sigma^2}
$$

不同码率方案进行编码增益比较时，将横轴转换为：

$$
\left(\frac{E_b}{N_0}\right)_{\mathrm{dB}}
=\left(\frac{E_s}{N_0}\right)_{\mathrm{dB}}+10\log_{10}R
$$

---

## 3. 正式冻结参数

三个方案均采用：

* 原始输入长度：300 bit；
* 基图：BG2；
* 最大迭代次数：32；
* 支持 syndrome 提前停止；
* 信道：离散BPSK-AWGN；
* NMS采用每个码长独立冻结的归一化因子。

| 方案   | 老师目标码长 | 实际码长 |     实际码率 | Zc | Filler | rankHp | NMS归一化因子 |
| ---- | -----: | ---: | -------: | -: | -----: | -----: | -------: |
| N480 |    480 |  480 | 0.625000 | 48 |     84 |     96 |     0.95 |
| N560 |  576附近 |  560 | 0.535714 | 56 |    148 |    112 |     0.95 |
| N640 |   ≤640 |  640 | 0.468750 | 40 |     20 |    320 |     0.80 |

N560没有精确命中576，原因是Direct构造受到允许提升因子、保留基图列数和校验子矩阵满秩条件限制。更接近576的候选没有通过可编码性Gate，因此冻结为最近的合法实际码长560。

---

## 4. BP与NMS译码方法

### 4.1 Layered BP

BP使用校验节点与变量节点之间的软信息迭代更新，校验节点包含 `tanh/atanh` 等非线性运算，主要作为译码性能基准。

优点：

* 译码性能较高；
* 软信息利用充分；
* 适合作为NMS的参考算法。

缺点：

* 非线性计算开销较大；
* 软件译码时延较高；
* 硬件实现复杂度较高。

### 4.2 Layered NMS

NMS使用最小和近似，并用归一化因子修正校验节点输出：

$$
L_{c\rightarrow v}
=

\alpha
\left(
\prod_{v'\in\mathcal{N}(c)\setminus v}
\operatorname{sign}(L_{v'\rightarrow c})
\right)
\min_{v'\in\mathcal{N}(c)\setminus v}
\left|L_{v'\rightarrow c}\right|
$$

其中：

$$
0<\alpha\le 1
$$

当：

$$
\alpha=1
$$

时，算法退化为普通Min-Sum，而不是带归一化修正的NMS。

NMS主要通过绝对值、符号、第一最小值、第二最小值和缩放运算替代BP中的复杂非线性计算。

---

## 5. NMS归一化因子的优化

早期实验曾冻结：

|  码长 |  早期α |
| --: | ---: |
| 480 | 1.00 |
| 560 | 1.00 |
| 640 | 0.80 |

后续审计发现，N480和N560在 $\alpha=1.00$ 时存在较多“错误合法码字快速早停”现象：

```text
syndrome通过
但恢复payload与发送payload不同
```

这会使译码时延看起来较低，但FER并不理想。原选择方法错误地把快速错误早停带来的低时延作为优势。

后续增加了：

* 逐帧payload、codeword和LLR哈希；
* correct-valid、wrong-valid、correct-invalid和wrong-invalid分类；
* early-stop与固定迭代对照；
* 不同α下的FER、时延和边消息更新次数曲线；
* BP/NMS结果独立性检查。

最终冻结：

| 实际码长 |  最终α |
| ---: | ---: |
|  480 | 0.95 |
|  560 | 0.95 |
|  640 | 0.80 |

---

## 6. 正式仿真参数

| 参数         | 正式配置                    |
| ---------- | ----------------------- |
| 输入长度       | 300 bit                 |
| 实际码长       | 480、560、640 bit         |
| 译码算法       | Layered BP、Layered NMS  |
| 信道         | BPSK-AWGN               |
| Es/N0范围    | -5.0～10.0 dB            |
| SNR步长      | 0.5 dB                  |
| SNR点数      | 31                      |
| 最小帧数       | 1000                    |
| 目标累计错误帧数   | 200                     |
| 最大帧数       | 50000                   |
| 最大迭代次数     | 32                      |
| 提前停止       | 完整迭代后检查syndrome         |
| BP/NMS公平性  | 共享payload、码字、噪声、LLR和帧范围 |
| Case数量     | 3                       |
| 算法数量       | 2                       |
| 正式记录数量     | 186                     |
| BP/NMS配对任务 | 93                      |

配对停止条件为：

$$
N_{\mathrm{frames}}\ge 1000
$$

且：

$$
N_{\mathrm{FE,BP}}\ge 200
$$

且：

$$
N_{\mathrm{FE,NMS}}\ge 200
$$

否则继续运行，直到：

$$
N_{\mathrm{frames}}=50000
$$

正式实验总配对帧数为：

$$
2,019,137
$$

BP与NMS合计译码评估帧次为：

$$
4,038,274
$$

---

## 7. 实验优化与问题修复

### 7.1 Direct NMS实现

原参考工程只有：

* Direct BP；
* 带速率匹配和恢复的标准链路NMS。

本实验以Direct BP Tanner图为基线，将NMS校验节点更新规则移植到Direct链路，实现了：

```text
Direct编码
+ Direct BP
+ Direct NMS
+ 无rateMatch/rateRecover
```

### 7.2 公平性优化

同一码长、同一SNR下，BP与NMS共享：

* payload；
* filler；
* codeword；
* BPSK序列；
* 高斯噪声；
* 接收符号；
* LLR；
* frameIndex；
* 停止帧范围。

由此避免随机样本差异影响算法比较。

### 7.3 元数据修复

正式后处理阶段曾错误地将N480和N560的部分Case元数据写成接近N640的参数。

已修复为：

| 方案   | 正确Zc | 正确Filler | 正确rankHp |
| ---- | ---: | -------: | -------: |
| N480 |   48 |       84 |       96 |
| N560 |   56 |      148 |      112 |
| N640 |   40 |       20 |      320 |

修复过程仅修改派生元数据，没有改变：

* 帧数；
* BER；
* FER；
* 迭代次数；
* 译码时延；
* 复杂度结果。

同时完成186条正式记录和93组checkpoint/chunk哈希核对，没有重新运行正式Monte Carlo。

### 7.4 零错误点处理

高信噪比下出现BER或FER为0时：

* CSV保留真实0；
* 不将0替换为伪造的小正数；
* 不连接零错误点；
* 不人为绘制高SNR水平error floor；
* 当前样本规模不足以证明存在error floor。

---

## 8. 正式实验结果

### 8.1 BP与NMS性能

BP与冻结后的NMS在BER和FER上非常接近。

在当前0.5 dB SNR网格及有限Monte Carlo统计精度下，可表述为：

> NMS相对BP的性能差异通常小于约0.1 dB，当前数据不能支持更高精度的性能差异结论。

### 8.2 译码时延

全SNR网格汇总中，NMS相对BP的平均软件译码时延下降约为：

| 实际码长 | NMS平均时延下降 |
| ---: | --------: |
|  480 |     77.8% |
|  560 |     76.5% |
|  640 |     74.1% |

该结果只代表当前Windows、Release编译和软件实现条件下的实测结果，不能直接等同于硬件译码时延。

建议优先使用：

* 平均译码时延；
* P95译码时延；
* 平均迭代次数。

最大时延容易受到操作系统调度影响，只作为异常观察指标。

### 8.3 平均边消息更新次数

NMS相对BP的平均边消息更新变化约为：

| 实际码长 | NMS相对BP变化 |
| ---: | --------: |
|  480 |   下降11.3% |
|  560 |    下降8.8% |
|  640 |    增加1.9% |

因此不能只根据边消息更新次数宣称NMS在所有码长下总体复杂度都更低。

NMS的主要优势是将BP中的 `tanh/atanh` 运算替换为绝对值、比较、符号和缩放等较低成本操作。

### 8.4 三码长相对编码增益

相对编码增益定义为：

$$
G_{\mathrm{candidate/reference}}
=\left(\frac{E_b}{N_0}\right)_{\mathrm{reference}}-
\left(\frac{E_b}{N_0}\right)_{\mathrm{candidate}}
$$

当：

$$
G>0
$$

表示候选方案在相同目标BER或FER下需要更低的 $E_b/N_0$。

在每类共同非零有效区间中取25个对数均匀目标点，对相邻非零实测点进行局部对数域插值，得到以下区间平均结果：

| 算法与指标   | N560相对N480 | N640相对N480 | N640相对N560 |
| ------- | ---------: | ---------: | ---------: |
| BP BER  |  -0.587 dB |  +3.462 dB |  +4.049 dB |
| BP FER  |  -0.576 dB |  +5.167 dB |  +5.742 dB |
| NMS BER |  -0.598 dB |  +3.591 dB |  +4.189 dB |
| NMS FER |  -0.532 dB |  +5.318 dB |  +5.849 dB |

上述数值是25个目标误码率点的平均值，只用于描述总体趋势，不代替具体目标BER/FER处的编码增益。

---

## 9. 结果结论

### N480

* 实际码率最高；
* 发送长度最短；
* 吞吐和传输开销较有优势；
* 在当前Direct构造下性能优于N560；
* 可靠性明显弱于N640。

### N560

* 对应老师要求的576 bit附近方案；
* 实际冻结为560 bit；
* filler达到148 bit；
* 在 $E_b/N_0$ 意义下没有优于N480；
* 平均相对编码增益约为负0.5～0.6 dB；
* 当前Direct列选择不是理想的中间码长设计。

### N640

* 实际码率最低；
* 冗余最多；
* filler仅20 bit；
* BER和FER曲线明显左移；
* 相对N480和N560具有显著可靠性收益；
* 适合作为可靠性增强扩展方案；
* 代价是发送长度增加和有效码率下降。

### BP与NMS

* BP作为性能基准；
* NMS与BP误码性能接近；
* NMS软件译码时延显著更低；
* BP/NMS下三码长性能排序基本一致；
* NMS更适合实时性和低复杂度实现，但需要关注错误合法码字早停。

---

## 10. 主要结果图

以下为主要结果图的相对路径。

### 正式BP/NMS结果

```text
Task/LDPC/block/stages/stage20_s4_final_integration/results/formal_ber.png
Task/LDPC/block/stages/stage20_s4_final_integration/results/formal_fer.png
Task/LDPC/block/stages/stage20_s4_final_integration/results/formal_avg_delay.png
Task/LDPC/block/stages/stage20_s4_final_integration/results/formal_avg_iterations.png
Task/LDPC/block/stages/stage20_s4_final_integration/results/formal_operation_count.png
```

### 三码长性能支撑图

```text
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/bp_length_ber_ebn0.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/bp_length_fer_ebn0.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/nms_length_ber_ebn0.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/nms_length_fer_ebn0.png
```

### 相对编码增益图

```text
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/bp_ber_relative_coding_gain_25points.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/bp_fer_relative_coding_gain_25points.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/nms_ber_relative_coding_gain_25points.png
Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/nms_fer_relative_coding_gain_25points.png
```

Markdown中可按以下方式插入：

```markdown
![NMS不同码长FER对比](相对路径/nms_length_fer_ebn0.png)

![NMS-FER相对编码增益](相对路径/nms_fer_relative_coding_gain_25points.png)
```

---

## 11. 主要结果数据和报告

```text
Task/LDPC/block/stages/stage20_s4_final_integration/results/s4_formal_point_results.csv

Task/LDPC/block/stages/stage20_s4_final_integration/results/s4_formal_bp_nms_comparison.csv

Task/LDPC/block/stages/stage20_s4_final_integration/results/s4_formal_length_comparison.csv

Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/relative_coding_gain_25_points.csv

Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/required_ebn0_by_target.csv

Task/LDPC/block/stages/stage22_length_relative_coding_gain/results/common_valid_ranges.csv

Task/LDPC/block/stages/stage23_s4_final_reintegration/results/s4_revised_final_report.md

Task/LDPC/block/stages/stage23_s4_final_reintegration/results/s4_revised_formal_point_results.csv

Task/LDPC/block/stages/stage23_s4_final_reintegration/results/s4_relative_coding_gain_25_points.csv
```

---

## 12. 核心程序与函数位置

### 12.1 核心接口

```text
Task/LDPC/block/current/include/s4_ldpc.hpp
```

主要内容：

* LDPC Case参数结构；
* Direct编码接口；
* BP/NMS译码接口；
* 译码trace；
* 停止状态；
* 迭代、时延和复杂度统计字段。

### 12.2 Direct编码、BP和NMS核心实现

```text
Task/LDPC/block/current/src/s4_ldpc.cpp
```

主要功能：

* BG2准循环矩阵展开；
* Direct GF(2)系统编码；
* $Hc^T=0$校验；
* Layered BP译码；
* Layered NMS译码；
* syndrome提前停止；
* wrong-valid分类；
* 迭代与操作计数。

### 12.3 仿真入口与正式runner

```text
Task/LDPC/block/current/src/main.cpp
```

主要功能：

* Case参数选择；
* BPSK与AWGN链路；
* payload、噪声和seed管理；
* BP/NMS配对仿真；
* checkpoint/chunk运行；
* BER、FER、时延和复杂度输出。

### 12.4 单元测试

```text
Task/LDPC/block/current/tests/unit_tests.cpp
```

主要测试：

* 参数合法性；
* 编码校验；
* 无噪声恢复；
* BP/NMS接口；
* 公平性与边界条件。

### 12.5 独立参考实现

```text
Task/LDPC/block/matlab/independent_reference.py
```

主要功能：

* 独立GF(2)矩阵构造；
* 独立编码参考；
* 码字一致性验证。

### 12.6 正式仿真控制

```text
Task/LDPC/block/scripts/formal_s4.py
```

主要功能：

* 正式SNR网格；
* 配对任务调度；
* checkpoint与恢复；
* 停止规则；
* 并行任务管理。

### 12.7 正式结果处理与绘图

```text
Task/LDPC/block/scripts/formal_postprocess.py
```

主要功能：

* 186条正式结果汇总；
* 数据一致性检查；
* BP/NMS比较；
* 时延与复杂度统计；
* 正式科研图生成。

### 12.8 相对编码增益处理

```text
Task/LDPC/block/scripts/revised_coding_gain.py
```

主要功能：

* $E_s/N_0$ 到 $E_b/N_0$ 转换；
* 共同有效非零区间确定；
* 25个对数均匀目标点生成；
* 局部对数域插值；
* 三码长相对编码增益计算；
* 中文结果图与sidecar生成。

### 12.9 审计脚本

```text
Task/LDPC/block/scripts/check_s4.py
Task/LDPC/block/scripts/check_alpha_rerun.py
Task/LDPC/block/scripts/check_alpha_rerun.py
```

主要功能：

* 结果schema检查；
* 参数与公式检查；
* BP/NMS公平性检查；
* alpha选择审计；
* 数值有限性和哈希检查。

---

## 13. Git记录

LDPC开发工作树曾为：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_LDPC
```

开发分支：

```text
stage01-ldpc
```

最终绘图修订提交：

```text
94b098f5
```

当前该分支已合并至：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design
```

主分支：

```text
main
```

---

## 14. 最终总结

本实验已经完成300 bit高速电文下Direct 5G NR LDPC的编译码实现、BP/NMS译码对比、NMS归一化因子优化、正式大规模仿真、三码长相对编码增益分析及结果审计。

最终结论为：

1. BP与NMS误码性能接近；
2. NMS能够显著降低当前软件实现下的平均译码时延；
3. N480是较高码率、较短发送长度方案；
4. N560当前Direct结构没有体现出相对N480的可靠性收益；
5. N640具有明显的BER和FER优势，适合作为可靠性增强方案；
6. 三码长的性能差异不仅来自码长，还受到实际码率、Zc、filler和校验矩阵结构共同影响；
7. 当前结果已经能够作为S5中卷积码与LDPC不同信道横向比较的正式LDPC基线。


---
