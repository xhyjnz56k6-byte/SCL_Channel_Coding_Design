# CC S3 集成总结

Stage01～14 Gate 全部 PASS，最终集成回归通过。正式 FER=0.1 的 hard 相对 soft 增益为 1/2 2.085 dB、2/3 1.927 dB、3/4 1.857 dB。码率越高 normalized goodput 上限越高，但达到相同 FER 需要更高 SNR。

推荐 Dtb70（明确为 fallback，最坏 BER/FER 损失 5.70%/12.99%，survivor 内存减少 77.12%）；推荐 receivedSymbols、clipMax2、Q6。整块零尾可靠性和边界最清晰；连续 window96/slide25 可提前输出，推荐 100×3 slots 作为实时折中，但 R23 存在已记录的小幅损失。
