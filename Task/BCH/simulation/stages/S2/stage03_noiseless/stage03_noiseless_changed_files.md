# stage03_noiseless 文件说明

- `cpp/`：8 Case 无噪声完整链路 runner。
- `matlab/`：分块独立参考与整块官方函数对照。
- `python/`：构建、运行和业务 checker。
- `results/`：8056 帧明细、Case 摘要及 8 个 MATLAB 样本对照。
- `logs/`：最终 CTest、MATLAB 和 checker 日志。

只链接 stage01/stage02 和既有 BCH 核心，不修改旧实现或旧结果。
