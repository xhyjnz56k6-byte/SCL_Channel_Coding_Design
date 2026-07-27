# stage10_cfo_formal 验证报告

Gate：`PASS_STAGE10_CFO_FORMAL`

- 24 个 trial 点与 40 个 formal 点均由当前 C++ runner 重新生成。
- 18 点达到 200 错帧停止；22 点达到 50000 帧上限；没有点超过上限。
- 14 点观测到原始零 BER/FER，CSV 保持 0；surrogate 仅用于对数图 `plotValue`。
- 30°末相位、逐 Case 相位增量、BER/FER 整数计数、实际码率和 SNR 公式全部复算通过。
- SNR 严格使用 `Eb/N0+10log10(payloadLength/encodedLength)`，未沿用 stage01 的 `2R` helper。
- 8 张 300 dpi PNG、8 份 figure-data、8 份 plot manifest 和全部 SHA-256 通过。
- MATLAB formal 抽查覆盖 K200/K300 的分块与整块/双块 Case，各取低/中/高点，共 12 样本；
  连续量误差不超过 `1e-12`，hard/payload/status mismatch=0。
- 图像目视抽查通过；中文字体为 Microsoft YaHei；无 PDF、NaN、Inf。
- 功能范围已包含在远程分支，`main` 未合并。

功能范围：`48ee1e8a71595dccc656a92576849fe03ff05467...3ec3e28cf6fe78f769a9878fe8683e634ed99217`。

共享 MATLAB repair 范围：`03e096c85b8afbbbfc8f74b9b161955c99ba0cea...5df70f96983ce4c339f7254e299ddd752514e259`。
