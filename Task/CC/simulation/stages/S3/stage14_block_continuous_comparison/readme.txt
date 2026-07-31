Stage14：整块与真实在线时隙组织对比

正式统一结果：results/stage14_online_slot_formal_results_all_decisions.csv
Hard 结果：results/stage14_online_slot_formal_results_hard.csv
Soft 结果：results/stage14_online_slot_formal_results_soft.csv

组织方式：A_BLOCK_300、B_CONT_50x6、C_CONT_100x3、D_CONT_150x2。
判决方式：Hard、Soft Float。码率：R12、R23、R34。
SNR = Es/N0：-5.0 至 10.0 dB，步长 0.5 dB。
停止条件：至少 1000 帧且达到 200 个帧错误，否则最多 50000 帧。

Block300 使用完整 Viterbi。连续方案保持编码器状态和打孔相位跨 slot 连续，
由 slot 到达更新接收缓存并触发真滑窗译码，最后统一终止。
