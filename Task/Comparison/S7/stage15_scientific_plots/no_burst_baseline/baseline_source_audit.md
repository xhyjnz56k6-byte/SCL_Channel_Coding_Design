# S7 无突发 AWGN 历史数据匹配审计

## BCH

采用 `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\BCH\simulation\stages\S1\stage07_awgn_dense_formal\published_results\stage07_awgn_dense_formal_results.csv` 的 `K200_S15`。原始 37 点逐行明确 `payloadLength=200`、`motherN/K/T=15/11/1`、`blockCount=19`、`encodedLength=285` 和 `actualRate=200/285`；Stage07 复用已审计 syndrome-lookup 硬判决链路。其 `sigma2=10^(-snrDb/10)`，与 S7 `sigma2=0.5*10^(-EsN0Db/10)` 严格等价于 `EsN0Db=snrDb-10log10(2)`。当前图只保留换算后落入 -5～10 dB 的 27 个原始点；未插值。

## CC

采用 `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\CC\simulation\stages\S3\stage09_awgn_formal\results\stage09_two_level_merged_point_results.csv` 的 `CC-B-R12-S`。Stage01/Stage09 冻结证据给出 payload=300、K=7、171/133、6 个零尾、N=612、SOFT_FLOAT、BPSK-AWGN 和 Es/N0。只抽取恰好落在 S7 -5～10 dB/0.5 dB 网格的 31 个原始点；密集层额外点未用于补点。

## 排除项

- BCH Stage06 `K200_M255K207`：编码结构和长度为 shortened BCH(255,207)/248 bit，不匹配。
- CC `CC-B-R12-H`：硬判决 Viterbi，不匹配 S7 软判决。
- Report frozen CC CSV：内容哈希与原始 Stage09 CSV一致，仅为重复副本，优先引用原始 Stage 文件。
- 打孔 R=2/3、3/4、连续未终止、其他 payload/码长及 Eb/N0 口径不明的数据均未使用。

## 时延与复杂度

两份历史 CSV 均含逐点平均译码时间；Stage15 使用帧数加权平均，仅作为纯译码 CPU 时间。历史结果没有与 S7 当前图一致的复杂度操作计数，因此复杂度基线明确为 N/A，不进行推断。无突发无交织的交织/解交织 CPU 为 N/A；buffer=0 是结构定义，不是历史仿真统计。

NO_FORMAL_RERUN
