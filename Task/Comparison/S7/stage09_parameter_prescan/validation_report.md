# Stage09 验证报告

- 原始行：612；候选：17；比较组：72；有区分度组：37。
- BER/FER 与计数一致、无 NaN/Inf：PASS。
- 同组 frames、payload、noise、burst start、frame sequence hash：PASS。
- 等跨度方法组：BCH FULL_FRAME_285；CC TRELLIS_SPAN_32/64/128。
- BCH 方法内参数：CODEBLOCK=19、ROW_COLUMN=15、GLOBAL=285。
- CC 方法内参数：SHORT_DEPTH=8、PSEUDORANDOM=128。
- 综合推荐：BCH_CODEBLOCK D=19；CC PSEUDORANDOM span=128。
- Formal：每编码 558 比较组；BCH 2232 点，CC 1674 点，共 3906 方案点。
- 资源估算：1000/5000/50000 帧约 0.19/0.97/9.70 单线程小时；最大约 770.5 MiB。
- checkpoint schema 与恢复 Gate：PASS（方案冻结；真实中断恢复须在 Formal 前小批量验证）。

Gate：PASS_PARAMETER_PRESCAN。Stage10 仍未授权。

