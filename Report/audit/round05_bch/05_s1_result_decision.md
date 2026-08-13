# S1 正式结果裁定

正式数值主表冻结为报告侧 `s1_01_five_case_formal_summary.csv`，源头为 BCH16W8 五方案合并结果。正式中文横轴图采用 BCH16W9 的六张图及逐图 CSV；其中 BER/FER 未重跑，只按实际码率精确转换横轴，译码时延使用修复 profile 重复构造污染后的独立三次中位数。

旧 `simulation/results/formal` 与 `bch15_awgn_formal` 是四方案历史主结果，现分类为 SUPERSEDED/AUDIT；其原始计数仍可追溯，但不再作为第4章五方案主表。BCH16W8 的旧时延列只作历史记录，正文时延使用 W9。

W9 六个 figure-data 共 222 行，`snrDb=sourceEbN0Db+10log10(frameRate)` 全部通过 1e-12 dB 检查。主文优先 200/300 bit FER 两图，BER 与状态细图移入附录候选。
