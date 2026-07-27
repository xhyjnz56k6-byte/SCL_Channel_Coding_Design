# stage02_case_contract 文件说明

- `cpp/`：8 Case 显式契约、统一编解码适配、契约测试和 CSV 导出。
- `matlab/`：独立长度和码率复算。
- `python/`：运行器和业务 checker。
- `results/`：Case、schema、长度、码率、图例、样式和 MATLAB 比较证据。
- `logs/`：最终成功运行的 CTest、MATLAB、导出和 checker 日志。

复用了 `Task/BCH/block/current` 和 `Task/BCH/segmented/current` 的已验证算法源码；
没有修改旧 Stage，没有复制旧正式 CSV 或 PNG。
