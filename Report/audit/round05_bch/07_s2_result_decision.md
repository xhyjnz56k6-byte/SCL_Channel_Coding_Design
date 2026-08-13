# S2 正式结果版本裁定

逐信道 MASTER 为 Stage07 dense AWGN、Stage08 common-SNR multipath、Stage10 dense 帧内线性相位漂移、Stage12 dense/ratio 遮挡和 Stage16 burst/interleaving。Stage06 coarse 是 AWGN 基线支持；Stage08 旧非 common-SNR 是被 common-SNR 版本替代的支持证据；早期 `batch2_corrected/published` 不再作为逐信道 MASTER。

Stage17 已验证五条分支的数值 checker，但最终全信道 Gate 因合并源分支的空白字符检查未通过，未生成 `PASS_BCH_S2_ALL_CHANNELS_INTEGRATION`。因此允许逐信道引用，不允许声称已完成严格的全信道统一排名。

轴口径裁定：Stage10、Stage12、Stage16 的 target `snrDb` 满足 `Es/N0=Eb/N0+10log10(R)`；Stage07 与 Stage08 的 waveform-SNR 定义满足 `waveformSnr=Es/N0+3.0102999566 dB`。后两者原图不得直接标为 Es/N0；只转换横坐标，不改原 CSV、噪声或 BER/FER。
