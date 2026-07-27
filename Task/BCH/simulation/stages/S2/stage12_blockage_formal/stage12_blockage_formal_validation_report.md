# stage12_blockage_formal 验证报告

Gate：`PASS_STAGE12_BLOCKAGE_FORMAL`  
组 Gate：`PASS_BCH_S2_CFO_BLOCKAGE_STAGE09_TO_STAGE12`

- 64 个固定 SNR/比例点与 40 个固定 10% 比例/SNR 点均由当前 runner 重新生成。
- 93 点达到目标错帧停止；11 点达到 50000 帧；无点超过上限。
- 8 点观测到原始零 BER/FER，原始 CSV 保持 0，绘图 surrogate 未反写。
- 每帧随机起点、区间边界、ratio→length、actual ratio、区内/区外原始误码和受影响码块统计通过。
- BER/FER/失败/误纠/未检出/真成功率均由整数计数复算通过。
- SNR 使用 `Eb/N0+10log10(actualRate)` 逐点转换。
- 10 张 300 dpi PNG、10 份 figure-data、10 份 plot manifest 和 SHA-256 通过；无 PDF。
- stage01–04 的 Release、CTest、checker 与 MATLAB/reference 回归全部 PASS。
- 已知限制：可选固定绝对长度实验 C 未执行；实验 A/B 完整。
- 功能范围已存在于远程分支，`main` 未合并。

功能范围：`10d85af8b99aeb44c118a312104348190c1bc997...8571880bb502e963d69f92460a1d582326128f77`。
