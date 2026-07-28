# Stage07 验证报告

Gate：`PASS_STAGE07_CC_BLOCK_NOISELESS`

- 分支：`stage01-cc`
- baseCommit：`493b0e33c53a1da8cd29f58b402ad3d5cb3e06f2`
- originalContent：`f75c99548ef481fb6822e67ddd0d947be3982a6e`
- repairContent：`2f5dba8c301c01a82530655c9765214068e58e27`
- mergeStatus：`NOT_MERGED`

六 Case 各执行 100 帧：payloadBitMismatch=0、payloadFrameMismatch=0、nonFiniteMetricCount=0。长度分别为 612/459/408，mask 观测数一致，finalState=0，actualRate 以 17 位记录并逐行验证 `300/N_transmitted`。checkpoint 基础 fixture 通过。Release build、CTest、Stage06 回归和 `git diff --check` 均通过。

原始提交的 actualRate 仅有默认 6 位，发现后未把 Gate 收口；修复输出精度和 checker 后完整重跑。

未运行 AWGN prescan/formal。远程验证延后至 Stage15 后统一 push；未合并 `main`。
