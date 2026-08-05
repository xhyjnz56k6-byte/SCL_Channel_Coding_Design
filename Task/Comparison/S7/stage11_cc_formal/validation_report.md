# Stage11 验证报告

- Stage10 BCH Formal Gate：PASS。
- Formal runner：PASS，2232 行、558 组、4 个配置各 558 行。
- 帧数范围：1000～48014；达到 50000 maxFrames 的结果行：0。
- 配置语义：D8（64 trellis steps）与 PSEUDO128 仅属于 `CC_RECOMMENDED_ENGINEERING_CONFIG`；D16 与 PSEUDO128 属于 `CC_EQUAL_SPAN_128` 受控对比；`pureMethodDifferenceAllowed=false`。
- BER/FER、计数、paired stopping、共享 payload/noise/burst/frame hash：PASS。
- NaN/Inf：0。
- 零 BER/FER 行：0；未写入伪小值、零错上界或水平延伸字段。
- stderr：空；runner 正常输出 `PASS_S7_FORMAL_RUNNER scheme=CC groups=558`。
- 结果 CSV：1672815 bytes；绝对路径记录于 `formal_validation.json` 和结果目录 readme。

Gate：PASS_CC_FORMAL。

