# Stage10 验证报告

- CMake build、CTest：PASS。
- syndrome table context 复用后 C++/MATLAB：72/72 PASS。
- checkpoint interrupt→resume 与 clean run：8/8 非计时行字段一致，无重复或跳帧。
- Formal runner：PASS，2232 行、558 组。
- 帧数范围：1000～50000；132 行达到 maxFrames。
- BER/FER 与计数、pair-stop、共享 payload/noise/burst/frame hash：PASS。
- NaN/Inf：0。
- 零 BER/FER 行：0；零值策略未触发伪值替换。
- detectedFailureFrames=0；undetectedFrameErrors=5439787；miscorrectedBlocks=23251548。该结果符合完美 Hamming 型 BCH(15,11,1) syndrome 对多错误模式误纠的限制，必须在结论中披露。
- 结果 CSV：1651356 bytes；绝对路径记录于 formal_validation.json。

Gate：PASS_BCH_FORMAL。
