# S5 高速电文不同信道对比仿真

本目录实现经 2026-07-31 用户批准的 S5 Stage01～Stage09。当前批次分支为 `S5-Compare`。

- `current/`：统一 C++ 复基带信道、CC/LDPC 接入、测试、配置、MATLAB/Python 参考。
- `stages/`：每个 Stage 的独立规格和审计记录。
- `results/`、`build/`：生成资产，默认不提交。
- `archive/`：失败或被替代的实验版本，只归档、不覆盖。

本轮只允许达到 `PASS_S5_SMOKE` 并冻结 Formal 参数；禁止执行 Formal。
