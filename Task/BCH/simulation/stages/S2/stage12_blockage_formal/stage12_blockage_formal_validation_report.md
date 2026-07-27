# stage12_blockage_formal 验证报告

Gate：`PASS_STAGE12_BLOCKAGE_FORMAL`

总 Gate：`PASS_BCH_S2_CFO_BLOCKAGE_STAGE09_TO_STAGE12`

- 实验 A：64 个固定 SNR/比例点已完成。
- 实验 B：40 个固定 10% 比例/SNR 点已完成。
- 实验 C：32 个固定绝对遮挡长度点已完成，长度为 `5、10、20、30` 个调制符号。
- A/B/C 合计 136 个正式点；20 点达到 50000 帧上限，其余点达到目标错帧停止条件，无点超过上限。
- 合计 13 个零 BER、13 个零 FER 观测点；原始 CSV 保持零，绘图 surrogate 未反写。
- 实验 C 的请求长度、实际长度、随机起点边界、实际比例和整数统计复算全部通过。
- BER/FER/失败/误纠/未检出/真成功率均由整数计数复算通过。
- SNR 使用 `Eb/N0+10log10(actualRate)` 逐点转换。
- A/B 的 10 张 PNG 与 C 的 6 张 PNG 均具有 figure-data、plot manifest 和 SHA-256；无 PDF。
- stage12 CTest、实验 C checker、原 stage12 checker 全部 PASS。
- MATLAB formal 抽查继续覆盖已冻结的同一遮挡模型，共 12 样本；连续量误差不超过 `1e-12`，hard/payload/status mismatch=0。
- stage01–04 的 Release、CTest、checker 与 MATLAB/reference 回归此前均已 PASS。
- 功能范围均已存在于远程分支；`main` 未合并。

原 A/B 功能范围：`10d85af8b99aeb44c118a312104348190c1bc997...8571880bb502e963d69f92460a1d582326128f77`。

共享 MATLAB repair 范围：`03e096c85b8afbbbfc8f74b9b161955c99ba0cea...5df70f96983ce4c339f7254e299ddd752514e259`。

实验 C 功能范围：`530551cfe22815a38eacaa683e97c82949d51c4c...03555c8813ca3d90b0a160cc63354b19110aff1f`。
