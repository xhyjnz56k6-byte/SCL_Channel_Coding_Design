# Stage12验证报告

- C++构建与执行：PASS。
- C++/MATLAB固定payload母码、R2/3发送位、无噪声译码payload逐bit一致：PASS。
- C++ R2/3擦除扫描：20点完成；另完成R1/2 5%擦除3点。
- MATLAB官方独立验证：8点完成，`poly2trellis/convenc/vitdec`链路PASS。
- R2/3固定trace选择frame 0和1，5%擦除起点分别92和282，位置具有代表性。
- 17×27全459符号交织/逆交织无损恢复：PASS；统计结果仅作诊断。
- C++ 5%擦除4/8/10 dB FER：0.998/0.998/0.998。
- MATLAB 5%擦除4/8/10 dB FER：0.999/0.999/1.000。
- 13项Stage12自动检查：13/13 PASS。
- Formal CSV SHA-256保持`dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947`。

Gate：`PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION`
