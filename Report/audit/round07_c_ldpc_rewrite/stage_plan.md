# Round07-C 第6章报告化重构

## 目标

将第6章重构为可直接提交的技术报告，按照设计、结构、译码、参数、仿真、性能、复杂度和工程选型展开，并以统一FER/BER口径增强定量分析。

## 非目标

- 不重跑LDPC正式Monte Carlo。
- 不修改正式CSV、正式PNG、译码算法、码长或归一化因子。
- 不修改第6章和附录A之外的报告正文。
- 不执行commit、push、merge或分支切换。

## 允许范围

- `Report/sections/06_LDPC方案与仿真分析.tex`
- `Report/appendices/A_完整参数表.tex`
- `Report/figures/ldpc/`中的正式PNG副本与说明
- `Report/audit/round07_c_ldpc_rewrite/`
- `Report/main.pdf`及编译中间文件

## 数据规则

- FER目标点使用相邻非零点的log10线性插值，禁止外推。
- 同一FER目标下的BER、平均/P95迭代和时间采用同一插值权重。
- 最大观测时间采用相邻采样点中的较大值，保留极端观测语义。
- 基础误码曲线使用Es/N0，相对编码增益使用派生Eb/N0。
- 正式输入和报告PNG副本通过SHA-256核对。

## Gate

- 第6章为10节正式技术报告结构。
- 研发词汇与写作元叙事扫描为0。
- 6.6至6.9均包含定量结果、机理解释和工程含义。
- 横向表固定FER或采用统一增益口径。
- 3个Visio占位、7个正式结果图组、8至11张表、5至6组公式。
- XeLaTeX成功，无未定义引用和Overfull。
- 正式CSV无Git差异，进入正文的PNG与源图哈希一致。

