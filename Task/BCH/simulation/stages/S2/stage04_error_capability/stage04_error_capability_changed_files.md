# stage04_error_capability 文件说明

- `cpp/`：逐独立码块错误注入、真值分类和固定样本导出。
- `matlab/`：16 个保证区关键样本独立/官方译码参考。
- `python/`：构建运行、保证区、边界覆盖和分类 checker。
- `results/`：错误用例、逐模式结果、状态摘要和 MATLAB 对照。
- `logs/`：CTest、MATLAB 和 checker 日志。

复用 stage02 冻结契约及既有 block/segmented 核心，未修改 stage01/stage02。
