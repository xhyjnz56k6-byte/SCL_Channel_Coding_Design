<h1 align="center">

以下是半成品的BCH信道多干扰测试的实验跟进记录

</h1>

---
````markdown
# BCH S2 多信道实验项目记录

## 1. 项目概况

### 1.1 实验名称

**低速电文 BCH 码不同信道条件下的性能比较**

### 1.2 实验目标

在输入信息长度为 200 bit 和 300 bit 的条件下，研究不同 BCH 编码方案在以下信道或干扰条件下的性能：

- AWGN 信道；
- 固定多径信道；
- 残余频偏；
- 短时遮挡；
- 连续突发错误；
- 交织前后的突发错误。

主要评价指标包括：

- 误比特率 BER；
- 误帧率 FER；
- 误纠率；
- 显式译码失败率；
- 真实译码成功率；
- 译码时延；
- 信道前处理时延；
- 端到端接收机时延。

本轮 S2 实验属于**探索性半成品实验**。现有代码和结果已经完成归档，可作为后续正式 S2 方案设计的参考，但不能直接作为最终最优方案结论。

---

## 2. 当前归档位置

### 2.1 C++ 程序

```text
Task/BCH/simulation/current/S2-test/
````

主要文件：

```text
Task/BCH/simulation/current/S2-test/include/bch_simulation/
├── bch_multipath_simulation.hpp
└── fixed_multipath_mmse.hpp

Task/BCH/simulation/current/S2-test/src/
├── bch_multipath_runner.cpp
├── bch_multipath_simulation.cpp
└── fixed_multipath_mmse.cpp

Task/BCH/simulation/current/S2-test/tests/
├── export_bch_s2_matlab_vectors.cpp
└── test_bch_s2_mmse.cpp
```

### 2.2 Python 驱动、检查和绘图程序

```text
Task/BCH/simulation/scripts/S2-test/
```

主要文件：

| 类型         | 文件位置                                |
| ---------- | ----------------------------------- |
| 实验运行       | `run/run_bch_s2_batch1.py`          |
| 结果检查       | `check/check_bch_s2_batch1.py`      |
| 文件归属扫描     | `check/scan_s2_ownership.py`        |
| AWGN 与多径比较 | `compare/compare_awgn_multipath.py` |
| 多径绘图       | `plot/plot_bch_s2_multipath.py`     |
| 最终审计       | `finalize/finalize_bch_s2_audit.py` |

### 2.3 MATLAB 独立参考程序

```text
Task/BCH/simulation/matlab_official_validation/S2-test/matlab/
└── run_bch_s2_multipath_reference.m
```

MATLAB 用于独立实现信道和接收机处理，并与 C++ 的逐帧结果进行比较，不能读取 C++ 最终结果作为算法真值。

### 2.4 Stage 审计目录

```text
Task/BCH/simulation/stages/S2-test/
```

主要 Stage：

```text
s2_01_channel_contract/
s2_02_multi_channel_foundation/
s2_03_awgn_baseline_reuse/
s2_04_fixed_multipath_mmse/
s2_batch1_fixed_multipath_mmse/
```

总索引：

```text
Task/BCH/simulation/stages/S2-test/S2_ARCHIVE_INDEX.md
```

迁移和归属清单：

```text
Task/BCH/simulation/stages/S2-test/s2_file_ownership.csv
Task/BCH/simulation/stages/S2-test/path_migration_manifest.csv
Task/BCH/simulation/stages/S2-test/results_migration_audit.csv
```

### 2.5 本地结果

```text
Task/BCH/simulation/results/S2-test/
```

目录包括：

```text
batch1/
batch2_original/
batch2_corrected/
burst_redesign/
```

该目录只在本地保存，没有加入 Git。

---

## 3. 公共实验参数

### 3.1 输入信息长度

```text
K_payload ∈ {200, 300} bit
```

### 3.2 当前已使用的 BCH Case

| Case         |    输入长度 | 编码方式               |  实际编码长度 |      码率 |
| ------------ | ------: | ------------------ | ------: | ------: |
| BCH-S200     | 200 bit | 19 个 BCH(15,11) 分块 | 285 bit | 200/285 |
| BCH-B200     | 200 bit | 缩短 BCH(255,207)    | 248 bit | 200/248 |
| BCH-S300     | 300 bit | 28 个 BCH(15,11) 分块 | 420 bit | 300/420 |
| BCH-B300     | 300 bit | 缩短整块 BCH           | 390 bit | 300/390 |
| BCH-B300-426 | 300 bit | 更强整块 BCH 方案        | 426 bit | 300/426 |

统一码率定义为：

$$
R=\frac{K_{\text{payload}}}{N_{\text{encoded}}}
$$

其中：

* $K_{\text{payload}}$ 为原始输入信息位数；
* $N_{\text{encoded}}$ 为实际发送的编码后比特数。

### 3.3 调制方式

采用 BPSK：

$$
x=
\begin{cases}
+1, & b=0 \
-1, & b=1
\end{cases}
$$

### 3.4 AWGN 信道

接收信号为：

$$
y=x+n
$$

其中：

$$
n\sim\mathcal{N}(0,\sigma^2)
$$

噪声方差为：

$$
\sigma^2=\frac{1}{2R\cdot 10^{E_b/N_0/10}}
$$

每一帧重新随机生成高斯噪声，不重复使用同一帧噪声。

### 3.5 SNR 换算

图中横轴统一记为：

```text
SNR（dB）
```

在带宽约定 $B_n=R_s$ 时：

$$
\mathrm{SNR}_{\mathrm{dB}}
==========================

\left(\frac{E_b}{N_0}\right)*{\mathrm{dB}}
+
10\log*{10}(R)
$$

### 3.6 误码率和误帧率

误比特率：

$$
\mathrm{BER}
============

\frac{\text{错误信息比特总数}}
{\text{发送信息比特总数}}
$$

误帧率：

$$
\mathrm{FER}
============

\frac{\text{译码后存在至少一个错误信息位的帧数}}
{\text{总仿真帧数}}
$$

---

## 4. S2-01：信道与指标规范冻结

### 4.1 实验目的

统一 S2 各实验的：

* Case 名称；
* 码率定义；
* SNR 定义；
* 随机数策略；
* 输出 CSV 字段；
* BER、FER 和时延定义；
* 图表和审计格式。

### 4.2 实验方法

对所有 S2 信道统一使用同一套帧生成、编码、调制、接收和统计接口。

每个信道只负责施加对应干扰，不允许修改 BCH 编码和译码核心算法。

### 4.3 优化内容

* 冻结码率为原始输入长度除以实际编码后长度；
* 每一帧独立生成噪声；
* 统一 Case 标识；
* 统一输出字段和随机种子；
* 统一记录配置哈希和数据哈希。

### 4.4 程序位置

```text
Task/BCH/simulation/stages/S2-test/s2_01_channel_contract/
```

---

## 5. S2-02：多信道公共基础设施

### 5.1 实验目的

建立可复用的多信道仿真接口，使相同 BCH Case 可以进入 AWGN、多径、频偏、遮挡和突发错误实验。

### 5.2 实验流程

```text
随机信息位生成
    ↓
BCH 编码
    ↓
BPSK 调制
    ↓
施加信道或干扰
    ↓
接收机前处理
    ↓
硬判决
    ↓
BCH 译码
    ↓
统计 BER、FER、误纠率和时延
```

### 5.3 优化内容

* 信道模块与 BCH 编译码模块解耦；
* 不同 Case 使用统一适配器；
* 统一随机数和噪声生成策略；
* 支持 smoke、formal、resume 和分片运行；
* 支持 C++ 与 MATLAB 使用相同冻结配置。

### 5.4 程序位置

```text
Task/BCH/simulation/stages/S2-test/s2_02_multi_channel_foundation/
```

---

## 6. S2-03：AWGN 基线复用

### 6.1 实验目的

复用 S1 已完成的 AWGN 正式结果，作为其他信道的参考基线，避免重复运行相同的大规模 AWGN 仿真。

### 6.2 实验方法

对已有 AWGN 数据执行：

* 数据文件存在性检查；
* 配置哈希检查；
* Case、码率和 SNR 换算检查；
* BER、FER 原始计数一致性检查；
* 数据源 SHA-256 检查。

### 6.3 使用原则

AWGN 基线只作为对照，不允许：

* 平滑数据；
* 插值生成新点；
* 修改原始 FER；
* 重新生成更“好看”的曲线；
* 使用外推补齐缺失点。

### 6.4 程序位置

```text
Task/BCH/simulation/stages/S2-test/s2_03_awgn_baseline_reuse/
```

---

## 7. S2-04：固定多径与 MMSE 均衡实验

### 7.1 实验目的

研究固定多径信道对不同 BCH 方案的性能影响，并比较经过 MMSE 均衡后相对于 AWGN 的 FER 损失。

### 7.2 信道模型

多径信道可表示为：

$$
y[k]
====

\sum_{l=0}^{L_h-1}h[l]x[k-l]
+n[k]
$$

其中：

* $h[l]$ 为固定多径抽头；
* $L_h$ 为信道抽头数；
* $n[k]$ 为高斯噪声。

### 7.3 MMSE 均衡

频域 MMSE 均衡权重为：

$$
W_{\mathrm{MMSE}}(f)
====================

\frac{H^*(f)}
{|H(f)|^2+\sigma^2/P_x}
$$

其中：

* $H(f)$ 为信道频率响应；
* $H^*(f)$ 为其共轭；
* $P_x$ 为发送信号功率；
* $\sigma^2$ 为噪声功率。

均衡输出为：

$$
\hat{X}(f)
==========

W_{\mathrm{MMSE}}(f)Y(f)
$$

### 7.4 实验方法

对每种 BCH Case：

1. 生成随机信息位；
2. 完成 BCH 编码和 BPSK 调制；
3. 通过固定多径信道；
4. 加入独立 AWGN；
5. 使用 MMSE 均衡；
6. 完成硬判决和 BCH 译码；
7. 统计 BER、FER 和时延；
8. 与相同 Case 的 AWGN 基线比较。

### 7.5 输出指标

* 多径条件下 BER；
* 多径条件下 FER；
* 相同 FER 目标处的 SNR 损失；
* MMSE 前处理时延；
* BCH 译码时延；
* 端到端时延。

若目标 FER 为 $P_t$，多径损失定义为：

$$
\Delta\mathrm{SNR}
==================

## \mathrm{SNR}_{\mathrm{multipath}}(P_t)

\mathrm{SNR}_{\mathrm{AWGN}}(P_t)
$$

仅当两条曲线均在原始采样区间内包络目标 FER 时才计算，不允许外推。

### 7.6 优化内容

* 增加固定多径信道模块；
* 增加 MMSE 均衡模块；
* 统一 AWGN 与多径的 SNR 语义；
* 使用 C++ 和 MATLAB 独立实现进行逐帧核验；
* 增加结果哈希、配置哈希和绘图审计；
* 区分信道前处理、译码和端到端时延。

### 7.7 代码位置

```text
Task/BCH/simulation/current/S2-test/include/bch_simulation/
├── bch_multipath_simulation.hpp
└── fixed_multipath_mmse.hpp

Task/BCH/simulation/current/S2-test/src/
├── bch_multipath_runner.cpp
├── bch_multipath_simulation.cpp
└── fixed_multipath_mmse.cpp
```

测试程序：

```text
Task/BCH/simulation/current/S2-test/tests/
├── test_bch_s2_mmse.cpp
└── export_bch_s2_matlab_vectors.cpp
```

Python 程序：

```text
Task/BCH/simulation/scripts/S2-test/run/run_bch_s2_batch1.py
Task/BCH/simulation/scripts/S2-test/check/check_bch_s2_batch1.py
Task/BCH/simulation/scripts/S2-test/compare/compare_awgn_multipath.py
Task/BCH/simulation/scripts/S2-test/plot/plot_bch_s2_multipath.py
Task/BCH/simulation/scripts/S2-test/finalize/finalize_bch_s2_audit.py
```

MATLAB 程序：

```text
Task/BCH/simulation/matlab_official_validation/S2-test/matlab/
└── run_bch_s2_multipath_reference.m
```

结果和审计：

```text
Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse/
Task/BCH/simulation/results/S2-test/batch1/
```

### 7.8 结果图位置

```text
Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse/
├── *.png
├── figure_data_*.csv
└── plot_manifest.json
```

### 7.9 结果记录表

|    输入长度 | Case         | AWGN FER | 多径+MMSE FER |    SNR 损失 | 结论            |
| ------: | ------------ | -------: | ----------: | --------: | ------------- |
| 200 bit | BCH-S200     |  见原始 CSV |     见原始 CSV | 见 summary | 分块方案对多径较敏感    |
| 200 bit | BCH-B200     |  见原始 CSV |     见原始 CSV | 见 summary | 整块方案整体性能更好    |
| 300 bit | BCH-S300     |  见原始 CSV |     见原始 CSV | 见 summary | 高码率区域性能下降明显   |
| 300 bit | BCH-B300     |  见原始 CSV |     见原始 CSV | 见 summary | 优于分块方案        |
| 300 bit | BCH-B300-426 |  见原始 CSV |     见原始 CSV | 见 summary | 冗余较多，FER 通常较低 |

准确数值以以下文件为准：

```text
Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse/formal_summary.csv
Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse/matlab_reference_summary.csv
Task/BCH/simulation/stages/S2-test/s2_04_fixed_multipath_mmse/figure_data_*.csv
```

---

## 8. S2-05：残余频偏实验

### 8.1 实验目的

研究接收端存在残余载波频偏时，不同 BCH Case 的 FER 变化。

### 8.2 修正后的频偏模型

主实验固定初始相位：

$$
\phi_0=0^\circ
$$

符号累计旋转为：

$$
\phi[k]
=======

\phi_0+k\Delta\phi
$$

接收信号为：

$$
y[k]
====

x[k]e^{j\phi[k]}+n[k]
$$

主实验只测量残余频偏，不再把多个初始相位混合进同一条曲线。

### 8.3 优化内容

旧实验曾将：

```text
0°、45°、90°、135°
```

四种初始相位聚合，导致零累计旋转处 FER 仍然很高。

修正后：

* 主曲线固定 $\phi_0=0^\circ$；
* 初始相位敏感性单独实验；
* 不再混淆初始相位误差与残余频偏；
* 重新生成逐点 CSV、PNG 和 manifest。

### 8.4 主要结果

在中间参考工作点，部分 FER 结果如下：

| Case         |     0° |    30° |    60° |
| ------------ | -----: | -----: | -----: |
| BCH-S200     | 0.0128 | 0.0264 | 0.5206 |
| BCH-B200     | 0.0106 | 0.0458 | 0.7762 |
| BCH-S300     | 0.0088 | 0.0206 | 0.5914 |
| BCH-B300     | 0.0092 | 0.0492 | 0.9042 |
| BCH-B300-426 | 0.0080 | 0.0568 | 0.9314 |

该结果说明：

* 小角度残余频偏下各方案仍可工作；
* 60°累计旋转会造成明显性能下降；
* 当前工作点下整块码不一定比短分块码更抗未经补偿的相位旋转。

### 8.5 本地结果位置

```text
Task/BCH/simulation/results/S2-test/batch2_corrected/
```

---

## 9. S2-06：短时遮挡实验

### 9.1 实验目的

研究一段连续符号出现幅度衰减时，不同 BCH 方案的 FER 变化。

### 9.2 遮挡模型

遮挡区间内：

$$
y[k]
====

a x[k]+n[k]
$$

其中：

$$
0<a<1
$$

遮挡外：

$$
y[k]
====

x[k]+n[k]
$$

### 9.3 实验变量

* 遮挡长度；
* 遮挡衰减；
* 遮挡起点；
* BCH Case；
* 参考 SNR。

### 9.4 优化内容

* 区分中度遮挡与重度遮挡；
* 使用随机合法遮挡起点；
* 禁止把长度 64 解释为精确临界值；
* 若在 64 处仍满足目标，只能记录为：

$$
L_{\text{tolerance}}\geq 64
$$

### 9.5 结果解释

遮挡性能与以下因素同时有关：

* 码长；
* 码率；
* 遮挡衰减；
* 遮挡长度；
* 遮挡位置；
* 接收 SNR。

因此不能仅根据单一遮挡曲线直接判断某种 BCH 对所有遮挡场景最优。

### 9.6 本地结果位置

```text
Task/BCH/simulation/results/S2-test/batch2_original/
Task/BCH/simulation/results/S2-test/batch2_corrected/
```

---

## 10. S2-07：连续突发错误与交织实验

### 10.1 实验目的

研究连续 bit 翻转对整块 BCH 和分块 BCH 的影响，并分析交织能否将连续错误分散到不同子块。

本实验中的突发错误不是物理信道波形模型，而是译码前的硬判决 bit 连续翻转模型。

### 10.2 突发错误模型

设连续错误长度为 $L$，起点为 $s$，则：

$$
r_i'=
\begin{cases}
1-r_i, & s\leq i<s+L \
r_i, & \text{其他}
\end{cases}
$$

### 10.3 整块 BCH 理论纠错区

对于纠错能力为 $t$ 的整块 BCH：

$$
L\leq t
$$

时，连续错误总重量不超过 $t$，应当保证正确译码。

当前整块 Case 的理论保证区：

| Case         | 理论纠错能力 |
| ------------ | -----: |
| BCH-B200     |  $t=6$ |
| BCH-B300     | $t=10$ |
| BCH-B300-426 | $t=14$ |

### 10.4 分块 BCH 理论纠错条件

BCH(15,11) 每个子块纠错能力为：

$$
t_{\text{sub}}=1
$$

若连续错误在每个受影响子块内均不超过 1 bit，则可保证纠正：

$$
\max_j e_j\leq 1
$$

其中 $e_j$ 表示第 $j$ 个子块中的错误数。

例如连续 2 bit 错误：

* 若两个错误位于同一子块，则该子块有 2 bit 错误，超过 $t=1$；
* 若两个错误跨越两个子块边界，则两个子块各有 1 bit 错误，可以分别纠正。

### 10.5 实验组成

#### S2-07A：整块 BCH 理论边界

验证：

```text
B200：L=1～6
B300：L=1～10
B300-426：L=1～14
```

理论保证区内应满足：

$$
\mathrm{FER}=0
$$

#### S2-07B：分块边界敏感性

研究：

* 子块内起点；
* 连续错误长度；
* 是否跨越 15 bit 子块边界；
* 每个子块实际承受的错误数。

#### S2-07C：随机突发错误

随机选择合法突发起点，对每个长度统计 FER。

#### S2-07D：交织前后比较

采用固定随机交织器，将连续错误映射到原编码帧的不同位置。

交织不改变错误总数：

$$
w_H(\mathbf{e}_{\text{before}})
===============================

w_H(\mathbf{e}_{\text{after}})
$$

但可能改变每个子块内的错误分布。

### 10.6 主要结果

* 三个整块 BCH Case 在 $L\leq t$ 的理论保证区内均实现 FER=0；
* S200 和 S300 在 $L=2$ 时，若错误跨子块边界，可正确恢复；
* 若 2 bit 错误集中在同一 BCH(15,11) 子块中，通常无法保证纠正；
* 固定随机交织显著降低分块 BCH 在短突发下的 FER；
* 交织不增加 BCH 的总纠错能力；
* 长突发条件下，交织收益逐渐消失；
* 对整块缩短 BCH，交织可能改变超保证区的具体错误位置，因此不保证一定改善。

部分结果：

| Case     | 条件           |      FER |
| -------- | ------------ | -------: |
| BCH-S200 | $L=2$，无交织    | 约 0.9060 |
| BCH-S200 | $L=2$，固定随机交织 | 约 0.0349 |
| BCH-S300 | $L=2$，无交织    | 约 0.9183 |
| BCH-S300 | $L=2$，固定随机交织 | 约 0.0356 |

### 10.7 本地结果位置

```text
Task/BCH/simulation/results/S2-test/burst_redesign/
```

---

## 11. S2-08：多信道综合比较

### 11.1 实验目的

将 AWGN、多径、残余频偏、遮挡和突发错误结果汇总，观察不同 BCH Case 的信道适应性。

### 11.2 比较原则

同一张 SNR 曲线图中：

* 横轴统一为 SNR；
* 纵轴统一为 FER；
* 不对数据平滑；
* 不重新插值生成曲线；
* FER=0 不用极小数替换；
* 不同曲线必须使用不同颜色、线型和标记；
* 同一输入长度单独绘图；
* 不把 200 bit 与 300 bit 混在同一性能结论中。

### 11.3 当前限制

当前比较仍未覆盖最终要求的完整方案矩阵。

后续正式实验应分别对 200 bit 和 300 bit 输入比较：

1. 分块 BCH(15,11)；
2. 缩短 BCH(255,207)；
3. 缩短 BCH(511,421)；
4. 缩短 BCH(511,385)。

并在每种信道下根据以下指标选出最优方案：

* FER；
* BER；
* 码率；
* 误纠率；
* 译码成功率；
* 时延；
* 复杂度。

---

## 12. S2-09：MATLAB 独立验证

### 12.1 实验目的

验证 C++ 信道模型、随机样本、接收机处理和离散译码结果是否正确。

### 12.2 验证内容

* 发送符号；
* 高斯噪声；
* 多径卷积结果；
* MMSE 均衡结果；
* 硬判决比特；
* 译码输出；
* BER、FER；
* 错误分类；
* 帧级状态。

### 12.3 验收标准

连续样本误差满足：

$$
\max_i |x_i^{\text{C++}}-x_i^{\text{MATLAB}}|
\leq 10^{-12}
$$

离散输出必须满足：

$$
N_{\text{mismatch}}=0
$$

### 12.4 程序位置

```text
Task/BCH/simulation/matlab_official_validation/S2-test/
```

---

## 13. 当前实验总体结论

1. 在 AWGN 和固定多径条件下，整块缩短 BCH 通常比 BCH(15,11) 分块方案具有更好的 FER 性能。
2. 分块 BCH 的主要问题是任意一个子块译码失败都会导致整帧错误。
3. 多径实验中的 MMSE 是接收机补偿方案，不是 BCH 编码算法的一部分。
4. 当前多径结果表示“固定多径经过 MMSE 补偿后仍剩余多少性能损失”，不能代表完全不均衡时的裸多径性能。
5. 残余频偏实验必须将初始相位误差和累计频偏分开研究。
6. 遮挡容忍长度若达到扫描上限，只能解释为下界，不能解释为精确极限。
7. 连续突发错误是否跨越 BCH(15,11) 子块边界，会显著改变分块码的译码结果。
8. 交织能够分散连续错误，但不能提高 BCH 本身的理论纠错能力。
9. 当前 S2 Case 矩阵不完整，因此暂时不能得出“某一种码长在所有信道下最优”的最终结论。
10. 本轮实验的主要价值是建立多信道基础设施、发现信道语义问题，并为下一版正式 S2 提供代码和参数参考。

---

## 14. 后续正式实验计划

后续正式 S2 应分别建立以下两组完整比较。

### 14.1 输入为 200 bit

| 方案              | 说明       |
| --------------- | -------- |
| 分块 BCH(15,11)   | 多子块独立译码  |
| 缩短 BCH(255,207) | 单整块编码    |
| 缩短 BCH(511,421) | 单整块或合法组帧 |
| 缩短 BCH(511,385) | 更强冗余方案   |

### 14.2 输入为 300 bit

| 方案              | 说明        |
| --------------- | --------- |
| 分块 BCH(15,11)   | 多子块独立译码   |
| 缩短 BCH(255,207) | 需要合法分块或组帧 |
| 缩短 BCH(511,421) | 单整块编码     |
| 缩短 BCH(511,385) | 更强冗余方案    |

每组均在以下信道下独立比较：

```text
AWGN
固定多径
残余频偏
短时遮挡
连续突发错误
```

最终输出：

```text
每种输入长度 × 每种信道 × 每种编码方案
```

对应的：

* BER；
* FER；
* 误纠率；
* 真实成功率；
* 译码失败率；
* 码率；
* 译码时延；
* 端到端时延；
* 最优方案和选择依据。

---

## 15. 文件快速索引

| 内容           | 路径                                                                                     |
| ------------ | -------------------------------------------------------------------------------------- |
| S2 C++ 代码    | `Task/BCH/simulation/current/S2-test/`                                                 |
| S2 Python 脚本 | `Task/BCH/simulation/scripts/S2-test/`                                                 |
| S2 Stage 审计  | `Task/BCH/simulation/stages/S2-test/`                                                  |
| S2 本地结果      | `Task/BCH/simulation/results/S2-test/`                                                 |
| MATLAB 独立参考  | `Task/BCH/simulation/matlab_official_validation/S2-test/`                              |
| 总归档说明        | `Task/BCH/simulation/stages/S2-test/S2_ARCHIVE_INDEX.md`                               |
| 文件归属表        | `Task/BCH/simulation/stages/S2-test/s2_file_ownership.csv`                             |
| 路径迁移表        | `Task/BCH/simulation/stages/S2-test/path_migration_manifest.csv`                       |
| 结果迁移审计       | `Task/BCH/simulation/stages/S2-test/results_migration_audit.csv`                       |
| 归档验证报告       | `Task/BCH/simulation/stages/S2-test/archive_reorganization_audit/validation_report.md` |

---

## 16. 记录状态

```text
项目状态：已完成半成品归档
实验性质：探索性参考实验
正式最优方案结论：尚未形成
原始结果：已保留
代码与结果：已分类存入 S2-test
results/S2-test：仅本地保存，未加入 Git
```

```
```
