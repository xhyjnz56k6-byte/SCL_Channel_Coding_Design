# Stage13 验证报告

- 输入：Stage10 BCH 2232 行、Stage11 CC 2232 行。
- 输出：8 个配置，每配置覆盖 558 个 Formal 点。
- frames 加权 decode/interleave/deinterleave 均值：PASS。
- T_add_cpu 恒等式：PASS。
- D8=64 trellis steps，D16/PSEUDO128=128 trellis steps：PASS。
- NONE 的 startupDelayBits/startupDelayTrellisSteps 均为 0：PASS。
- `physicalLatencyClaimAllowed=false`：8/8。
- 原始数据绝对路径存在：8/8。

Gate：PASS_STAGE13_LATENCY_COMPLEXITY。
