# stage01_foundation 文件说明

- `cpp/`：新增 AWGN 数学、BPSK、完整随机身份、单元测试和固定向量导出器。
- `matlab/`：新增独立 AWGN 数值参考。
- `python/`：新增构建运行、C++/MATLAB 比较和业务 checker。
- `results/`、`logs/`：保存本阶段小型可审计向量和实际日志。
- 根目录 CSV/JSON/Markdown：保存冻结配置、验收矩阵、测试摘要和哈希。

安全复用来源为 `Task/Common` 的数学定义、既有 BCH 编解码 Stage 的审计记录和旧
BCH AWGN 流水线结构。没有复用旧正式结果 CSV 或 PNG。
