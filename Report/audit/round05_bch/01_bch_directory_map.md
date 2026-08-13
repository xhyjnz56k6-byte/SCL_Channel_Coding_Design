# BCH 定向目录图

## 当前实现

- BCH 根目录：`Task/BCH`
- 分组码当前实现：`Task/BCH/segmented/current/{include,src,tests}`
- 整块码当前实现：`Task/BCH/block/current/{include,src,tests}`
- 统一仿真当前实现：`Task/BCH/simulation/current/{include,src,tests}`
- S1 正式阶段：`Task/BCH/simulation/stages/bch15_awgn_formal`、`bch16w6_formal_awgn`、`bch16w8_five_case_comparison`、`bch16w9_decode_timing_snr_figures`
- S2 正式阶段：`Task/BCH/simulation/stages/S2/stage06_awgn_formal` 至 `stage16_burst_interleaving_comparison`
- S2 汇合证据：`Task/BCH/simulation/integration/stage17_all_channels_integration`
- 公共直接依赖：`Task/Common/include/common`、`Task/Common/src`
- 报告章节：`Report/sections/04_BCH编码方案与仿真分析.tex`（已存在，未新建重复文件）
- 报告侧冻结数据：`Report/data/frozen/bch`
- 既有报告证据：`Report/evidence/round03/{s1,s2}`、`Report/evidence/round04`

## 结果与版本位置

- 旧 S1 四方案结果：`Task/BCH/simulation/results/formal`
- S1 五方案合并结果：`Task/BCH/simulation/stages/bch16w8_five_case_comparison`
- S1 报告横轴/时延修订：`Task/BCH/simulation/stages/bch16w9_decode_timing_snr_figures`
- S2 早期综合树：`Task/BCH/simulation/results/S2-test/batch2_corrected/published`
- S2 当前逐信道正式树：`Task/BCH/simulation/stages/S2/stage07_*`、`stage08_*`、`stage10_*`、`stage12_*`、`stage16_*`

## 分类

- `current` 与上述逐信道正式 Stage：当前实现或正式证据。
- `build`、point/shard/checkpoint、frame-detail：生成物或运行细节，不进入正文清单。
- `archive`、`backup`、旧 batch 原始树：历史或被替代证据，仅在版本冲突追溯时使用。
- `batch2_corrected/published`：旧综合发布候选；固定初相位等遗留专题可作附录证据，但不能覆盖后续逐信道 Stage。

本图为定向索引，不是全仓库 inventory。
