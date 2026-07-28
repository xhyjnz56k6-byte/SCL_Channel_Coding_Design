# Stage14 规格冻结：整块与连续滑窗比较

在 R12-soft@0 dB、R23-soft@1 dB 各 500 个相同 payload/母噪声帧比较 A整块零尾、B50×6、C100×3、D150×2。B/C/D 使用 Stage12 连续编码语义和 Stage13 window96/slide25/Dtb70；每帧只生成一次编码与接收符号。

连续方案只在最后统一追加 6 个尾 bit，因此 A-D 当前有限 300 bit 实验的 N_transmitted 相同；其优势相对于“每 slot 独立清零加尾”的反事实是避免 `(slotCount-1)*6` 个重复 tail input bits。A 的内部 boundaryBitCount=0、boundaryBER 记 0 并由报告说明 N/A。

验收要求覆盖 BER/FER、四区域 BER、长度/码率、输出时延、译码时延/吞吐/goodput、内存、ACS/traceback 操作，并保证逐方案分区计数闭合。

Gate：`PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON`
