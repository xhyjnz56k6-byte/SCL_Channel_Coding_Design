# stage05_awgn_trial 变更说明

- `cpp/`：24 点试运行、原始计数、checkpoint/resume 与三分片等价验证；
- `python/`：构建驱动、正式停止规则边界测试、业务 checker 与可复现绘图；
- `configs/`：8 Case 各 3 点及固定随机种子；
- `plots/`：4 张 300 dpi PNG、逐图数据和 plot manifest；
- `logs/` 与 Stage 根目录：真实 Gate 日志、规格、验收矩阵及冻结配置。

完整机器可读文件清单以 `stage05_awgn_trial_manifest.json` 的 functional range 为准。
