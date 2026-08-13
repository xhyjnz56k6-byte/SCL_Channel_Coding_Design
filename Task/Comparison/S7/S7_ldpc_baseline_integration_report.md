# S7 LDPC 无交织近码率基线集成报告

## 要求与范围

老师新增要求为“LDPC 不配置交织，仅保留无交织基线对照”。本轮只读扫描独立工程 `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_LDPC\Task\LDPC\block`，优先审计 stage15～stage23 Formal、validation、最终配置、结果、时延、复杂度和推荐记录；没有重跑 S7 或 LDPC Formal，也没有修改独立 LDPC 工程。

## 候选与选择

完整候选见 `stage15_scientific_plots/ldpc_baseline/ldpc_candidate_inventory.csv`。正式 payload=300 候选为 N480、N560、N640，每个均有 SPA/BP 和 NMS；实际码率分别为 0.625、0.5357142857142857、0.46875。N640 与 CC 最接近，Stage12R 和最终 Formal 配置明确冻结 N640 NMS alpha=0.80，因此不存在译码器歧义。

- configurationId：`LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80`
- payloadBits：300；informationBits：320；fillerBits：20
- transmittedBits：640；baseGraph：2；liftingSize：40；rateMatching：NO
- LDPC actualRate：300/640 = 0.46875
- CC actualRate：300/612 = 0.49019607843137253
- absolute rate difference：0.02144607843137253
- relative rate difference：0.04375（4.375%）
- decoder：Direct Layered NMS，alpha=0.80，maxIterations=32，FLOAT_LLR_SOFT
- interleaver：NONE
- comparisonRole：`NO_INTERLEAVING_NEAR_RATE_REFERENCE`

## 信道与统计兼容性

- channel：LDPC 为 BPSK + AWGN、无突发；没有 2%/5%/10% 连续极性反转结果。
- SNR：双方均为 Es/N0，均使用 `sigmaSquared=1/(2*10^(EsN0Db/10))`，无需转换。
- BER：双方均统计原始 300-bit payload，分母为 `300 × frames`。
- FER：双方均在 payload 至少存在一个错误 bit 时记为帧错。
- 2% burst：N/A；5% burst：N/A；10% burst：N/A。
- 结论边界：不能由 LDPC AWGN 曲线推断其突发容限，也不能写成“LDPC 抗 2%/5%/10% 突发”。

## 时延与复杂度

两套程序均用 `steady_clock` 只包围译码函数，因此时延定义可作软件实现 CPU 时间参考。跨 SNR 按实际帧数加权后，CC 历史无突发软 Viterbi 为 428650.005 ns/帧，LDPC N640 NMS 为 93743.162 ns/帧。该结果不等价于硬件时延或硬件复杂度，不用于无条件宣称某编码复杂度更高或更低。

复杂度没有共同 operation-count 口径：CC 为固定 306 trellis steps、64 states、branch metrics/ACS；LDPC 为 N=640、2240 edges，加权平均 1.7604 iterations、3943.31 edge-message updates。未把一次 ACS 与一次边更新等价，统一复杂度数值为 N/A。LDPC 交织附加缓冲量为 0；这不包含 LDPC 译码器内部消息存储。

## 图表修改

修改 5 张现有 CC 图：

- `01_methods_fer`
- `02_methods_ber`
- `03_burst_2_fer`
- `04_burst_5_fer`
- `05_burst_10_fer`

新增 1 张图：

- `22_cc_ldpc_no_burst_decode_latency`

LDPC 统一使用紫色复合虚线、空心五边形，并在图例中标记 AWGN 与真实码率。位置图、全起点热力图、FER 改善图、交织缓冲图和推荐排名均未加入 LDPC。

新增或刷新表格：

- `stage15_scientific_plots/ldpc_baseline/ldpc_candidate_inventory.csv`
- `stage15_scientific_plots/ldpc_baseline/selected_ldpc_baseline_points.csv`
- `stage15_scientific_plots/results/cc/coding_baseline_comparison/coding_baseline_comparison.csv`
- `stage15_scientific_plots/results/cc/coding_baseline_comparison/coding_complexity_reference.csv`
- `S7_coding_reference_summary.csv`

`S7_coding_reference_summary.csv` 的 LDPC burst 字段使用 N/A，不使用 0。LDPC 不进入 `recommendation_ranking.csv`。

## 归档

5 张修改前旧图位于各图 `archive/v01_20260811_before_ldpc_baseline_integration/`。Stage15 总清单、Stage16 验证结果以及 S7 顶层表格/报告分别在其最近的同名 archive 版本中保留。归档包含旧数据、manifest、validation、README 和 SHA。

## 数据保护与 Gate

- S7 BCH Formal rerun：NO
- S7 CC Formal rerun：NO
- LDPC Formal rerun：NO
- interpolation：NO
- smoothing：NO
- synthetic data：NO
- LDPC selected source SHA256：`6c72c89fbac5e846fc7a68483dc18fa5e2238cd9740e48b2d29163ea0c6e5e3e`
- S7 Stage10 SHA256：`adbd8d2499b220525195fb115c989469ed00e0965d5f69ed6d28637f48ad4c9d`
- S7 Stage11 SHA256：`86f7ff8e46712406714887050d06de8ccd55e0c47ed7e6facd92c09556db886d`
- BCH 历史原始 CSV SHA256：`337c1cb6f46dc8239482f9183738375dc5f7f1f8c9b320e03d5b238a310a6843`
- CC 历史原始 CSV SHA256：`0efd6914aca0415c0e7f7a888f8eb749d699f9f7e4f08625678746dc161fae25`

独立 LDPC 仓库在本轮开始前已存在 23 个 stage `readme.txt` 修改，因此不是 clean。本轮用开始状态行和这些 dirty 文件 SHA 前后完全一致证明没有新增或改变 LDPC 工程修改，而不伪称其原本 clean。

Gate R～AB 的来源、payload、码率、SNR、BER、FER、无重跑、无合成、位置图和排名限制见 `ldpc_baseline_source_audit.csv`。Gate AC～AF 的归档、外部工程状态和输入 SHA 验证通过，input SHA mismatch=0。Stage15 实际输出 `PASS_S7_STAGE15 plots=51`；Stage16 实际输出 `PASS_S7_STAGE16_FINAL_AUDIT`。

## Git

- branch：`S8-PaperDocu`
- git status：dirty；修改与新增均限定在 `Task/Comparison/S7/`，无 staged 文件、无删除、无独立 LDPC 工程新增修改
- commit：NO
- push：NO
- merge main：NO
