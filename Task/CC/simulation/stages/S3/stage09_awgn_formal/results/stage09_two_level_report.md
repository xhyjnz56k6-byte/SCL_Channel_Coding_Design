# Stage09 两层网格复核

- 新 coarse：186 行，4620252 frames，6 Case × 31 点，-5～10 dB/0.5 dB。
- dense：126 行，825696 frames；明确标记为归档中的上一轮 verified dense，并记录 sourceCommit/sourceRun。
- 合并曲线：282 行；dense 在相同 Case/SNR 上覆盖 coarse。
- 模型：符号级离散 BPSK-AWGN，不是完整连续波形仿真。
