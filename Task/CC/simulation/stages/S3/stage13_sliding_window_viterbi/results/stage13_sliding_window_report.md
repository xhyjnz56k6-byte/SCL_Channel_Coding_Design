# Stage13 滑窗 Viterbi 报告

候选检查拒绝 window=64 和 slide>window 的组合，选择 `windowInputBits=96`、`slideStepBits=25`、`Dtb=70`。无噪声 hard/soft 均恢复 300 bit，输出索引严格为 0～299，首次发布时刻为 input time 74，平均决定延迟 71.38 input bits。

500 帧小规模 AWGN 中，R12-soft@0 dB 与完整块 mismatch=0；R23-soft@1 dB 有 77 bit/8 frame mismatch，分布为 head26、boundary16、middle32、tail3，已完整解释且未隐藏。survivor memory=13440 bytes，window buffer=1536 bytes。Stage14 将把该真实差异带入整块/连续比较。
