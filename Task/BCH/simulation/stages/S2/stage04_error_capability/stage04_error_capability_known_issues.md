# stage04_error_capability 已知问题

- 超能力区出现大量 BCH(15,11,1) 误纠，这是实际查表译码行为，不是 Gate 失败。
- 本阶段不评估 AWGN 分布下的发生率；这里只验证固定错误图样。
- 生成明细保留在本地 `results/`。
- 当前 AWGN 功能分支未 push；仅 stage01/02 基线已单独同步。
