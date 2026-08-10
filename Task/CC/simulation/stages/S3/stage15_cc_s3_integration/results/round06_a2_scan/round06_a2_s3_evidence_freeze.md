# Round06-A2：卷积码 S3 正式结果裁定与第5章证据冻结

## 1. 扫描范围

本轮定向读取 `Task/CC/Plan`，S3 Stage09～15 当前 `readme`、正式报告、summary/recommendation/selection CSV、manifest、figure_data、当前 PNG，以及附件指定的 trellis、打孔、整块编码、Hard/Soft Viterbi、真滑窗、Stage14 和 Stage15 关键源码。为确认后续引用，只定向读取了 `Task/Comparison/S5`、`S6`、`S7` 的冻结配置和最终报告。

未扫描 `build/`、`runtime/`、`checkpoint/`、分片 unit CSV、Stage08 过程图、临时缓存和 archive 内容；未完整复核 S5/S6/S7 实验结果。原因是本轮只裁定 S3 权威证据，且当前正式 CSV、runner 和下游冻结文件已满足停止条件。

## 2. S3 最终设计逻辑

S3 的工程链条不是文件堆叠，而是逐层回答问题：

1. **码率与判决（Stage09）**：以同一 300 bit、K=7、171/133、BPSK-AWGN 模型，改变 R12/R23/R34 和 Hard/Soft，回答冗余度与软信息能带来多少可靠性收益。
2. **回溯（Stage10）**：在 Stage09 的 FER≈0.30/0.10/0.03 工作点改变 Dtb，回答接近完整回溯需要多深、节省多少 survivor 存储以及付出多少回溯/输出等待代价。
3. **量化（Stage11）**：改变 Q3～Q8/Float，回答软判性能能否用有限位宽实现。正式选择为 Q8；Q6虽接近Float，但不是当前 recommendation CSV 的最终 balanced 选择。
4. **连续发端接口（Stage12）**：验证状态、打孔相位、尾部和checkpoint，不承担性能结论。
5. **真滑窗（Stage13）**：分别改变 W、S、D，回答缓存覆盖、触发/输出节奏、回溯可靠性的独立作用，再形成每码率 performance/balanced/latency 候选。
6. **真实时隙（Stage14）**：改变 Block300/50x6/100x3/150x2 与 Hard/Soft，回答相同最终码流在不同到达粒度下为何可靠性相同而首输出和P95不同。
7. **最终推荐（Stage15）**：在固定 Es/N0 或固定目标 FER 两类公平口径下，给出 reliability/throughput/latency/memory/balanced 五类方案。

与早期计划相比，实际执行扩大并收紧了证据：Stage10 从早期 R12/R23、D35/49/70 扩为三码率六深度；Stage11 从 Float/3/4/6 bit 扩为 Q3～Q8/Float；Stage13 全量控制实验采用 W实验固定S16/D70、S实验固定W160/D70、D实验固定W160/S16，而非早期文档中的 W128 固定条件；Stage14 从先做单码率Soft扩为三码率、Hard/Soft、四组织完整网格。

## 3. Stage09～15 权威源裁定

权威明细见 `round06_a2_stage_authority_matrix.csv`。裁定摘要如下：

- Stage09：正式点源是 `stage09_two_level_merged_point_results.csv`；当前主图可追溯到同一 merged CSV。
- Stage10：正式点源是 `stage10_traceback_study_results.csv`；最终深度必须同时看 recommendation CSV，不能用旧计划。
- Stage11：正式点源是 `stage11_soft_quantization_results.csv`；Q3～Q8和Float全部运行。
- Stage12：只有接口/回归正确性权威，不是BER/FER正式结果。
- Stage13：控制变量权威源是 `stage13_full_wsd_formal_results.csv`，最终候选权威源是 `stage13_final_comparison.csv` 与 `stage13_final_recommendations.csv`。
- Stage14：Hard/Soft统一权威源是 `stage14_online_slot_formal_results_all_decisions.csv`。
- Stage15：对外总矩阵、工作点和推荐分别以 `stage15_final_scheme_matrix.csv`、`stage15_fair_operating_points.csv`、`stage15_final_recommendations.csv` 为准。

各 Stage 均存在 archive/旧结果，但本轮未把 archive 作为当前证据。没有发现当前正式 CSV 与生成 runner 之间无法裁定的冲突。

## 4. 正式参数冻结

### 4.1 编码与信道

- payload 300 bit；K=7；记忆6 bit；64状态。
- 171/133（八进制）母码，母码率1/2；zero-tail 6 bit；306 trellis steps；母码612 bit。
- R12/R23/R34 打孔分别为 `11`、`1101`、`110110`，发送长度612/459/408，实际码率分别为0.4901960784/0.6535947712/0.7352941176。
- SNR定义为 Es/N0，`sigma²=1/[2·10^(Es/N0/10)]`。若换算 Eb/N0，必须用实际帧级码率。
- Stage09 coarse 为 -5～10 dB、0.5 dB步长，实际 stopping metadata 为1000/200/50000；dense 是已验证的 waterfall 密集点，实际 metadata 为5000/200/50000。两者不能被早期计划或runner默认值覆盖。

### 4.2 关键源码事实

- `trellis.cpp` 的next-state与抽头异或对应K=7、171/133，状态范围0～63。
- `block_encoder.cpp` 只在整帧最终追加6个0并校验终止状态0。
- depuncture 对删除位置填0但 `observed_mask=0`；Hard/Soft分支度量都只累计 observed 位置，因此删除比特是“无观测”而不是判为0。
- Hard Viterbi 使用逐输出位Hamming距离；Soft Float 使用接收BPSK样本与候选±1符号之间的平方欧氏距离。**正式Float Soft并非直接以LLR为分支度量。**
- 真滑窗仅分配 `W×64` survivor，满足 `W>D`、`S<=W-D`；非最终窗口每次提交S个payload bit，最终窗口从终止状态0回溯并flush剩余payload，源码检查无丢失/重复。
- Stage14 连续编码器跨slot携带encoder state与puncture phase，只有final slot调用终止/尾比特；三种连续组织拼接后的发送流一致。

完整参数与数值见 `round06_a2_ch5_parameter_freeze.csv`。

## 5. 第5章正式结果冻结

### 5.1 码率与Hard/Soft

由 `stage15_fair_operating_points.csv` 直接核验，Block Float Soft 在 FER=0.1 的插值 Es/N0 为：R12 -0.708611 dB、R23 0.963104 dB、R34 1.884527 dB。Hard减Soft的SNR差为2.084523/1.926990/1.857441 dB。

共同 Es/N0=2.0 dB 时必须区分两种口径：

- Stage15最终候选：R12 Block=0（有限样本零误帧观测）、R23 sliding balanced=0.00616067、R34 sliding balanced=0.07160759。
- 全部Block Float Soft基线：R12=0（有限样本观测）、R23=0.00729049、R34=0.0762。

因此“0/0.006161/0.07161”成立，但不能写成“三码率Block Float Soft结果”。任何0值只表示当前帧数下没有观察到误帧，并不等于理论FER严格为0。

### 5.2 回溯Dtb

Stage10实际正式测试35/49/70/84/98/112和完整回溯。`stage10_traceback_recommendation.csv` 的最坏相对FER增幅随Dtb为4.45、1.28、0.291、0.125、0.0676、0.0338；在5% Gate下只有D112通过，所以有限回溯通用正式选择为D112，不是D84。

在Stage15选取的三码率FER≈0.1点，D84相对FER增幅中位数为0.07（最坏0.11），D112中位数为0.005（最坏约0.005）。D112总译码内存22528 B，对比完整回溯59776 B减少约62.3%，首次判决等待由305降至111 symbols；代价是连续有限回溯约21840 operations/frame，高于完整块的一次306-step回溯，且本机平均CPU时间342.672 us高于完整块288.388 us。D84进一步降至17152 B和83 symbols，但可靠性Gate不通过。CSV中的CPU时间仅是本机Release软件观测，不可当作跨平台硬件时延。

### 5.3 量化

Q3～Q8与Float均完成正式运行。Stage15矩阵只保留Float/Q4/Q6/Q8是汇总降维。Q8相对Float在FER=0.1的损失为R12 0.006214 dB、R23 0.008130 dB、R34 -0.000741 dB；负微值按采样和插值波动解释。正式balanced/performance/latency推荐均为Q8；Q4仅为memory-first，Q6不能替代Q8写成最终选择。

### 5.4 真滑窗W/S/D

实际全量集合为 W={96,128,160,192}（固定S16/D70）、S={8,16,25,50}（固定W160/D70）、D={35,49,70,84,98,112}（固定W160/S16），三码率均使用同一控制集合。最终候选按码率不同：

- R12 balanced W128/S25/D70；latency/memory W96/S16/D70。
- R23 balanced W128/S25/D98；latency/memory W128/S25/D84。
- R34 balanced W160/S25/D126；latency/memory W128/S25/D98。

D126只存在R34候选/最终比较数据；Stage15报告明确没有把D126补跑到全量D控制网格，不能声称全量正式D集合包含126。

### 5.5 时隙组织

Stage14正式比较A_BLOCK_300、B_CONT_50x6、C_CONT_100x3、D_CONT_150x2，Hard/Soft Float各372行。连续三组织在每个码率、判决、SNR点的BER/FER完全重合，因为最终发送流、接收序列、滑窗边界和终止规则相同；slot粒度改变符号到达时刻，所以首输出、平均和P95不重合。

Soft首次输出最小值223 symbols由R23/50x6和R23/150x2并列；R23/50x6的P95为256 symbols，低于R23/150x2的397，因此综合低时延组织选择50x6。

## 6. 最终推荐

五类方案已由 recommendation CSV 与 scheme matrix 双重核验，详见 `round06_a2_s3_recommendation_freeze.csv`：

- reliability_first：`R12_BLOCK_SOFT_FLOAT`。
- throughput_first：`R34_SLIDING_BALANCED`，W160/S25/D126。
- latency_first：`R23_SLIDING_LATENCY_FIRST`，W128/S25/D84。
- memory_first：`R12_SLIDING_LATENCY_FIRST`，W96/S16/D70。
- balanced：`R12_SLIDING_LATENCY_FIRST`，W96/S16/D70。

这些推荐不是一个统一硬件默认配置；reliability/throughput采用固定Es/N0比较，另外三类采用固定FER=0.1比较。

## 7. 进入S5/S6/S7的方案

- **S5多信道CC/LDPC横向比较**：使用两个整块Float Soft方案，R23/459 bit与R12/612 bit，均为完整306步终止回溯；不使用滑窗W/S。
- **S6译码复杂度**：使用R12/612 bit，包含整块Hard、整块Float Soft，以及50x6/100x3/150x2三种slot组织各自的Hard和Float Soft；slot统一W128/S25/D70。
- **S7交织专题**：基础卷积码是R12、300/612、整块Float Soft、完整306步终止回溯，不采用连续编码或滑窗。交织位于卷积编码之后、信道之前，以trellis-step为单位保持171/133输出对；接收端先对软值解交织，再进入Soft Viterbi。相对推荐PSEUDORANDOM span=128 trellis steps。

逐行映射见 `round06_a2_downstream_mapping.csv`。

## 8. 第5章图表建议

正文优先采用Stage15的七码率/判决/回溯/量化/滑窗/时隙图，附录保留BER、Hard时隙、goodput、Stage13控制变量和Stage14边界图，清单见 `round06_a2_ch5_figure_selection.csv`。

当前Stage15正式PNG经直接查看与绘图脚本核验，标题和坐标轴均为英文（如“Block300 Float Soft FER by rate”“SNR = Es/N0 (dB)”）；Stage10～14当前科研图也以英文标签为主。数据和figure_data是正式可用的，但第5章中文正文不应直接把英文图当最终版。后续只需基于figure_data中文重绘，不需要重跑仿真。本轮按要求不擅自重绘。

高SNR零错误点保留在正式CSV，但当前对数图省略零值，不绘成人工水平error floor；这是正确策略。archive、Stage08过程图、临时/历史PNG禁止进入正文和附录。

## 9. 当前仍存在的不确定项

1. Stage09 dense标记为 `dense_verified_legacy`，其正式CSV含sourceCommit/sourceRun且已通过当前合并检查，足以作为正式证据；但若第5章要求逐条重现dense原始命令，需另查归档运行记录，本轮不展开。
2. 现有Stage15推荐全部是Float方案；Q8是量化研究的工程候选，但没有被强行替换进五类系统推荐。因此报告应分开写“性能推荐”与“量化实现推荐”。
3. R34 balanced使用D126，而全量D控制变量最高为112。该候选有正式最终比较数据，但不能用于声称“D126完成全量控制变量网格”。
4. 当前PNG尚未中文化；不影响数据裁定，但影响第5章最终排版交付。

以上均不是BLOCKING，也不要求重跑S3。

## 10. 是否需要重新跑仿真

**NO_RERUN_REQUIRED**。

理由：Stage09～15权威CSV、runner、推荐表和下游引用已经闭合；关键数值可由正式CSV直接复核；已发现的差异都是口径或汇总范围差异，可以通过准确表述解决。后续工作仅是基于现有figure_data进行中文科研绘图和第5章写作，不需要重新运行S3正式仿真。
