# S6 译码算法对比与结果汇总

## 1. 任务目的与数据来源

本任务在 `S6-Comparision` 分支完成本地已有结果盘点、BCH 必要补跑、Stage11 全部 86 图中文重绘、CC/LDPC 历史 Formal 整合和 S6 科研图汇总。BCH 使用本轮 Release 单线程正式结果；CC 来源于 Stage14；LDPC 来源于 Stage23 修订后的 N560 Formal 点表。

## 2. BCH 方案与正式实验

- BCH-S200：200 bit 分组方案，19 个 shortened BCH(15,11,1)，N=285，syndrome lookup，每段 t=1。
- BCH-B200：200 bit 整块 shortened BCH(255,207)，N=248，BM+Chien，t=6。
- 信道为 BPSK+AWGN；Es/N0=-5:0.5:10 dB；minFrames=1000、targetFrameErrors=200、maxFrames=50000。
- 62/62 点完成，噪声公式、停止条件、计数、存储和计时 Gate 全部通过。

S200 与 B200 是不同码型、不同组织、不同码率、不同纠错能力的工程组合对比。不能把 BER/FER 差异全部归因于 lookup 与 BM。

## 3. 复杂度、存储与时延定义

BCH 复杂度分为算法事件、有限域/位操作、存储和实测译码时间。不同操作类别并非等价硬件代价，因此不生成无定义的单一复杂度总和。存储按对象、表、缓冲区和峰值工作区分类；BCH 使用 `EXACT_FROM_TYPE_AND_COUNT`。译码计时从输入硬判决准备完成开始，到 payload 与状态就绪结束，不包含编码、信道、硬判决、日志和文件 I/O。

## 4. CC 硬软判决与组织方式

整合 R1/2、K=300、N=612 的 BLOCK_HARD、BLOCK_FLOAT_SOFT，以及 B/C/D 三种时隙组织的 Hard/Float Soft，时隙统一 D=70、W=128、S=25。Hard=1 bit，Float Soft=Float。CPU 译码时间与首输出/决策符号时延严格分列。

Hard/Soft 是判决信息方式；Block/Slot 是组织与调度方式。两者是独立维度。历史结果非严格 pair-stop，本次未重跑 CC Formal。

## 5. LDPC BP/NMS

只使用 Direct BG2 N560：K=300、N=560、Zc=56、filler=148、parity=112、maxIter=32。BP/NMS 的 31 对 SNR 点共用 payload、codeword、LLR 和 syndrome early-stop；NMS alpha=0.95。

BP 是性能基准。NMS 以较低非线性复杂度换取可能的性能损失。现有主结果为 maxIter=32；代码支持不等于 10/20/30 正式结果存在。

## 6. BER/FER 与零值处理

所有原始零值保持为 0。高 SNR 零 BER/FER 点不参与对数曲线绘制，`plotValue` 留空且 `isPlotted=false`；未平滑、未插值、未绘制人工下限线。曲线终止不代表存在真实 error floor。

## 7. 图与结果清单

- Stage11 中文重绘：86 张，86/86 通过逐图 Gate。
- S6 最终科研图：BCH 10、CC 8、LDPC 8，共 26 张。
- 详细结果、指标和图清单见 `S6_result_inventory.csv`、`S6_metric_summary.csv` 和 `S6_plot_inventory.csv`。

## 8. 工程选型建议

- BCH：若重视实现简单和分段局部纠错，可评估 S200；若重视整块 t=6 能力，可评估 B200，但须连同码率和码型差异解释性能。
- CC：Hard 降低输入精度与部分存储需求，Float Soft 提供更丰富可靠度信息；Block/Slot 应按调度与实时延迟需求另行选择。
- LDPC：BP 用作性能基准，NMS 在本平台显著降低非线性运算与平均 CPU 时间，但必须结合实际 BER/FER 曲线判断可接受损失。

## 9. 环境与限制

正式 BCH CPU 为 Intel(R) Core(TM) i5-14400F，编译器为 g++.exe (Rev8, Built by MSYS2 project) 15.2.0，Release、单线程。时延仅适用于当前 CPU、操作系统、编译器、Release 配置和线程环境；最大时延是平台相关观测值，不是理论最坏上界。完整环境见 `S6_environment_summary.md`。

## 10. Gate 与 Git 状态

20 项最终 Gate 全部 PASS。当前 HEAD 为 `9d51fabdaa8446966f70c395d552576b3ab7fb52`；工作区按任务要求保持未提交。未运行 CC Formal，未运行 LDPC Formal，未 commit、未 push、未 merge，且未合并 main。

S6_FINAL_STATUS = PASS
