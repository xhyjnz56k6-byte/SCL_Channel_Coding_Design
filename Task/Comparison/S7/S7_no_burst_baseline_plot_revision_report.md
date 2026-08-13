# S7 无突发 AWGN 基线绘图修订报告

## 1. 老师新增要求与执行边界

本轮在适用的 BCH/CC BER、FER 和纯译码时间正式图中增加“无突发信道（AWGN）”基线，以区分“无突发”“有突发无交织”“有突发有交织”三个层级。没有重跑 Stage10/11 Formal，没有修改历史 CSV、编译译码算法、交织、信道、SNR 网格或停止规则。

`NO_FORMAL_RERUN`

## 2. BCH 历史无突发数据源与匹配证据

源 CSV：

`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\BCH\simulation\stages\S1\stage07_awgn_dense_formal\published_results\stage07_awgn_dense_formal_results.csv`

使用 `K200_S15`：payload=200，19×BCH(15,11,1)，encoded=285，rate=200/285，硬判决 syndrome lookup，BPSK-AWGN，无交织、无突发。历史 Stage07 的 `sigma2=10^(-snrDb/10)` 与 S7 的 `sigma2=0.5×10^(-EsN0Db/10)` 给出严格口径换算 `EsN0Db=snrDb-10log10(2)`。换算后仅使用落入 S7 展示范围的 27 个原始点，不插值、不平滑。

## 3. CC 历史无突发数据源与匹配证据

源 CSV：

`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\CC\simulation\stages\S3\stage09_awgn_formal\results\stage09_two_level_merged_point_results.csv`

使用 `CC-B-R12-S`：payload=300，K=7，171/133（八进制），mother rate=1/2，6 个零尾，306 trellis steps，encoded=612，FLOAT_SOFT terminated Viterbi，BPSK-AWGN，无交织、无突发，横轴为 Es/N0。只抽取 -5～10 dB、0.5 dB 步长的 31 个原始粗网格点；密集层非 S7 网格点没有用于补点。

## 4. 排除的数据源

- BCH `K200_M255K207`：shortened BCH(255,207)、encoded=248，与 S7 结构不符。
- CC `CC-B-R12-H`：硬判决 Viterbi，与 S7 FLOAT_SOFT 不符。
- CC R=2/3、3/4：打孔码率不符。
- Report 下冻结 CC 副本：内容有效但与原始 Stage09 CSV 重复，正式图优先引用原始 Stage 路径。
- 码长、payload、终止方式、译码方式或 SNR 口径不明的其他历史 CSV：均未使用。

逐项审计见 `stage15_scientific_plots/no_burst_baseline/baseline_source_audit.csv` 和 `baseline_source_audit.md`。

## 5. 修改与归档清单

重绘 14 张，正式总数保持 BCH 29、CC 21、合计 50：

- BCH：`01_methods_fer`、`02_methods_ber`、`03_burst_2_fer`、`04_burst_5_fer`、`05_burst_10_fer`、`16_decodeTimeMeanNsWeighted`、`22_burst_5_ber`、`23_burst_10_ber`。
- CC：`01_methods_fer`、`02_methods_ber`、`03_burst_2_fer`、`04_burst_5_fer`、`05_burst_10_fer`、`16_decodeTimeMeanNsWeighted`。

上述每图旧资产均归档到各图目录的 `archive/v01_20260811_before_no_burst_baseline_update/`；旧图允许历史审计，不允许继续作为当前正式报告图。新图 `figure_data.csv` 的每个基线点包含历史源绝对路径、Stage、配置和源行键。

## 6. 三层结果分析

### BCH

- 无突发 AWGN：约 -0.0103 dB 时 FER=1；约 4.9897 dB 时 FER≈0.0620；约 9.9897 dB 为零错观测，原始 0 保留且对数图不画。
- 2% 突发：5 dB 的突发无交织 FER≈0.8444，最佳交织约 0.4024；10 dB 最佳交织约 3.33×10^-4，已接近相邻 9.9897 dB 的无突发零错观测，但不能把不同横坐标点相减为精确增益。
- 5% 突发：5 dB 的突发无交织 FER≈0.9975，最佳交织约 0.6798；10 dB 最佳交织约 7.63×10^-4，显示高 SNR 下仍有显著恢复。
- 10% 突发：到 10 dB 仍全部 FER=1，进入饱和失效区。

### CC

- 无突发 AWGN：0 dB 时 FER≈0.02068；2 dB 及以上为零错观测，对数图不画零值点。
- 2% 突发：0/5/10 dB 最佳交织 FER 分别约 0.895/0.5438/0.4489；虽相对突发无交织 FER=1 有恢复，但与无突发基线仍相差很大。
- 5% 突发：10 dB 最佳交织 FER≈0.9945，仅恢复约 0.0055，基本失效。
- 10% 突发：全部测试高 SNR 点仍饱和为 FER=1。

原有 FER absolute improvement/relative reduction 定义没有改变，仍是“有突发无交织”减“有突发有交织”；本报告没有把其改名为无突发损失。

## 7. 时延、置换开销、缓冲与复杂度

- BCH 历史无突发纯译码时间的纳入点帧数加权平均约 10226.5 ns。
- CC 历史无突发纯译码时间的纳入点帧数加权平均约 428650.0 ns。
- 这些柱只表示 `T_decode`；`T_interleave`、`T_deinterleave` 和 buffer wait 没有混入。
- 跨 Stage CPU 时间受编译环境、计时实现和机器负载影响，只作描述性参考，不能把差值直接归因为突发或交织。
- 历史无突发实验没有交织，交织/解交织 CPU 基线为 N/A；没有使用 identity 接口耗时冒充附加置换时间。
- 无突发 AWGN 和无交织结构的 interleaver buffer 均为 0；这是结构参数，不是历史仿真统计。
- 历史结果没有与 S7 当前图一致的复杂度操作计数，因此复杂度基线为 N/A，未构造理论操作数或推断值。

## 8. 原始输入 SHA 前后对比

| 输入 | SHA256（修改前=修改后） |
|---|---|
| Stage10 BCH Formal | `adbd8d2499b220525195fb115c989469ed00e0965d5f69ed6d28637f48ad4c9d` |
| Stage11 CC Formal | `86f7ff8e46712406714887050d06de8ccd55e0c47ed7e6facd92c09556db886d` |
| BCH 历史 AWGN | `337c1cb6f46dc8239482f9183738375dc5f7f1f8c9b320e03d5b238a310a6843` |
| CC 历史 AWGN | `0efd6914aca0415c0e7f7a888f8eb749d699f9f7e4f08625678746dc161fae25` |

## 9. Gate 与 Git 状态

- Gate A～O：PASS；配置严格匹配、无合成、无插值、无平滑、输入 SHA 不变、逐点可追溯、归档完整、位置图无假基线、时延源合法、复杂度明确 N/A、图 SHA 已更新。
- Stage15 Gate：PASS，50/50。
- Stage16 Gate：PASS。
- 当前分支：`S8-PaperDocu`。
- Git status：DIRTY，仅包含本轮 S7 绘图脚本、基线审计、正式图/归档、inventory/manifest/report/SHA 更新；没有 Stage10/11 或历史源 CSV 修改。
- Commit：NO。
- Push：NO。
- Merge：NO。

`PASS_S7_NO_BURST_BASELINE_PLOT_REVISION`
