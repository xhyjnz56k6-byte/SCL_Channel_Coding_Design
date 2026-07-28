# Stage10 回溯深度研究报告

在 R12-soft 的 -0.5/0.0 dB 与 R23-soft 的 0.5/1.0 dB 各运行 1000 帧，共比较完整块和 `Dtb={35,49,70}`。

严格优先门限（所有点 BER/FER 增幅均不超过 5%）没有候选通过。Dtb=70 的最坏 BER 增幅为 5.696%，最坏 FER 增幅为 12.987%，survivor 内存由完整块的 58752 bytes 降至 13440 bytes（减少 77.124%），满足已记录的 fallback 门限，因此冻结为 Stage12 候选。

四场景合计的 full mismatch frames：Dtb35=774、Dtb49=368、Dtb70=96。四场景平均 `firstStableOutputDepth` 为 45.225。当前研究实现为每个输出重复回溯，四场景平均时延约为 full=488.174 us、Dtb35=540.897 us、Dtb49=535.381 us、Dtb70=543.749 us；因此 Dtb70 的价值是性能与内存折中，不代表该离线实现已获得时延收益。Stage12 必须用滑窗调度重新验证时延。

推荐：`Dtb=70`，等级 `FALLBACK`。不得表述为与完整块无损等价。
