# 正文图候选

## 可直接使用

1. S1 200 bit FER：`Task/BCH/simulation/stages/bch16w9_decode_timing_snr_figures/figures/bch_200bit_fer_snr_cn.png`。
2. S1 300 bit FER：`Task/BCH/simulation/stages/bch16w9_decode_timing_snr_figures/figures/bch_300bit_fer_snr_cn.png`，同时呈现 B300-390 与 B300-426。
3. S2 帧内线性相位漂移 FER：Stage10 的 K200/K300 FER 图，横轴已符合 Es/N0 定义。
4. S2 遮挡 FER：Stage12 的 K200/K300 `fer_vs_snr`，必要时另选一张 `fer_vs_ratio`。
5. S2 突发/交织：Stage16 plot-revision 的 K200/K300 FER overview；正文最多选一张，详细图留第9章或附录。

## 转换后使用

- Stage07 AWGN dense K200/K300 FER。
- Stage08 multipath common-SNR K200/K300 FER。

这两组原图横轴是 `waveformSnr=2Es/N0`，进入第4章前必须从横坐标减去 3.0102999566 dB，并在新图源同时保留原 `snrDb`、转换后的 `esN0Db` 和 `actualRate`。只转换横轴，不修改 BER/FER。

## 附录候选

S1 BER、true/reported/miscorrection/failure 全套图；各信道时延分位数；固定初相位历史灵敏度图；Stage14/15 全部突发长度和交织深度图。正文不放全量结果。
