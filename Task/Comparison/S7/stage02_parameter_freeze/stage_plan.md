# Stage02 参数冻结

冻结内容见 `../configs/s7_smoke_frozen_config.json` 与 `s7_formal_frozen_config.json`。主 Formal 只允许未知连续 BPSK 极性反转叠加 AWGN；CC 伪随机单位固定为 TRELLIS_STEP、保持母码输出对、跨度 32/64/128。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| JSON 可读 | configs | JSON parse | null 主参数或错误类型 | Smoke 配置完整 |
| CC 约定 | Smoke config | unit test pair | span=31 | 仅 32/64/128 |
| C++/MATLAB | 计划/config | fixed trace | tie/状态约定不同 | Stage08 逐项一致 |
| Formal 锁 | Formal config | authorized=false | 未确认启动 | Stage10 不执行 |

