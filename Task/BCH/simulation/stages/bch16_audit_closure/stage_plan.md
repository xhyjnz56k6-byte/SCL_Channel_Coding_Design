# BCH-B300-426 批次审计收口

目标：收口 BCH-B300-426 核心、MATLAB 官方 codec、AWGN smoke/prescan/formal 与五方案比较结果。

范围：`Task/BCH/block/current`、`Task/BCH/simulation/current`、`Task/BCH/simulation/matlab_official_validation/matlab` 及本批次 `stages/bch16w*` 证据摘要。

非目标：不修改 CC/LDPC，不覆盖旧 BCH-15/BCH-16V 结果，不合并 `main`。

验收矩阵：

| 需求 | 正向证据 | Gate |
|---|---|---|
| BCH(426,300) 参数与生成多项式 | `bch16w1_bch511_385_core/parameter_compare_summary.csv` | PASS |
| C++ 编码译码 | `bch16w2_bch426_300_codec/cpp_codec_summary.csv` | PASS |
| MATLAB 官方 codec | `bch16w3_matlab_official_codec/matlab_official_codec_summary.csv` | PASS |
| AWGN smoke/prescan/formal | `bch16w5_awgn_prescan/`, `bch16w6_formal_awgn/` | PASS |
| 五方案比较与绘图 | `bch16w8_five_case_comparison/` | PASS |
| MATLAB 官方逐帧 formal 对比 | 未生成 W7 证据 | NOT_RUN |

