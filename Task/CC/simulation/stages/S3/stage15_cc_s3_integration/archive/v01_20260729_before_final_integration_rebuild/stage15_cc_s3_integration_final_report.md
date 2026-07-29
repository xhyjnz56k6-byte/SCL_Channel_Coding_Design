# CC S3 集成总结

Stage01～14 Gate 全部 PASS，最终集成回归通过。正式 FER=0.1 的 hard 相对 soft 增益为 1/2 2.085 dB、2/3 1.927 dB、3/4 1.857 dB。码率越高 normalized goodput 上限越高，但达到相同 FER 需要更高 SNR。

推荐 Dtb70（明确为 fallback，最坏 BER/FER 损失 5.70%/12.99%，survivor 内存减少 77.12%）；推荐 receivedSymbols、clipMax2、Q6。整块零尾可靠性和边界最清晰；连续 window96/slide25 可提前输出，推荐 100×3 slots 作为实时折中，但 R23 存在已记录的小幅损失。

## 最终问题回答

1. soft 相对 hard 提升见上述三组 FER=0.1 增益。
2. R12 冗余最大、低 SNR 最稳；R34 actualRate 最高、goodput 上限最高但瀑布右移；R23 居中。
3. 回溯深度推荐 70，属于性能优先 fallback。
4. 软量化推荐 Q6，Q3/Q4 在当前门限下不合格。
5. 整块适合离线/可靠性优先；连续滑窗适合低首输出时延。
6. 推荐 100×3、window96、slide25、Dtb70。
7. 连续组织避免每 slot 重复尾比特；本 300 bit 统一终止实验 actualRate 与整块相同，滑窗性能损失会降低 successful goodput。
8. 后续 LDPC 对比基线采用六个整块 Case，主基线 R12-soft，吞吐扩展用 R23-soft。
9. 性能、时延和量化结论仅适用于 300 bit、当前 SNR、MinGW/Windows 软件环境与冻结随机策略。
10. S5/S6/S7 复用 Stage09 六 Case、公共 frame/noise key、R12/R23 soft 主线及整块公平定义。
