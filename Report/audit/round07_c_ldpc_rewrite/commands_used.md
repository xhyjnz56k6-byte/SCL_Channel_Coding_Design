# Round07-C 执行命令与方法

本轮不重跑 Monte Carlo，不修改 `Task/LDPC` 源码、正式 CSV 或正式 PNG。所有定量结论均由既有正式结果离线整理得到。

- 读取归一化因子扫描 CSV、正式点结果 CSV、码长元数据 CSV 和相对编码增益 CSV。
- 使用 PowerShell/Python 对相邻非零 FER 点执行 `log10(FER)` 线性插值，并以同一权重插值得到迭代、时间和复杂度指标；不外推到正式数据范围以外。
- 使用 SHA-256 核对 7 个正式输入 CSV，以及正文引用的 13 个 PNG 副本与源图。
- 使用 XeLaTeX 编译 `Report/main.tex`；最终 PDF 共 109 页。
- 使用 pypdfium2 将第 6 章打印页 74--90 和附录 A.5 打印页 99 渲染为 PNG，逐页检查图表顺序、分页、溢出和留白。
- 执行正文禁用元话语扫描、LaTeX 日志扫描、`git diff --check`、`Task/LDPC` 零差异检查和 Git 工作区检查。
- 未执行提交、推送、合并、分支切换或正式仿真。
