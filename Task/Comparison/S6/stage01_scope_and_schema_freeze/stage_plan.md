# Stage01 规格冻结

## 目标

- 冻结 BPSK+AWGN、Es/N0=-5.0:0.5:10.0 dB、31 点正式网格。
- 冻结停止条件 minFrames=1000、targetFrameErrors=200、maxFrames=50000。
- BCH 仅 S200/B200，新增动态复杂度、存储和统一时延并正式重跑。
- CC 仅整理 R1/2 Block Hard/Float Soft 与 D=70/W=128/S=25 的已有 Slot Hard/Float Soft。
- LDPC 仅整理 N560、maxIter=32、BP/NMS、alpha=0.95 的已有正式结果。
- 冻结零 BER/FER 不绘制但保留原始值的政策。

## 非目标

- 不重扫 CC W/S/D，不重跑 CC Formal。
- 不优化 LDPC alpha，不运行 LDPC 10/20/30 全网格 Formal。
- 不重新设计 BCH 码型，不把 S200/B200 的差异完全归因于译码算法。
- 不修改历史原始 CSV，不平滑、插值或伪造实验点。

## 允许范围

- `Task/Comparison/S6/**`
- BCH 必要的计数接口、实现、测试和 S6 专用正式 runner。

## 禁止范围

- 无关工程；历史原始 CSV；未归档旧结果；main；Git 历史。

## 数据与公式

- `sigmaSquared=1/(2*10^(EsN0Db/10))`
- `EbN0Db=EsN0Db-10*log10(actualRate)`
- BER=`bitErrors/(processedFrames*payloadBits)`
- FER=`frameErrors/processedFrames`
- 零错误上界仅保存 `3/processedFrames`，不画入主曲线。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| S6 范围冻结 | 本 Stage 文档 | 配置逐项检查 | 禁止出现 N480/N640 主 Case | PASS_REPOSITORY_SCOPE |
| BCH schema | result_schema.csv | 必需字段齐全 | 缺列检查失败 | PASS_BCH_RESULT_SCHEMA |
| BCH 计数 | Stage02 | 无噪声、单错、0~6错 | 非法长度/无效计数 | PASS_BCH_COUNTER_UNIT_TESTS |
| BCH 存储 | Stage02 | 方法和值合法 | 方法缺失/负值失败 | PASS_BCH_MEMORY_ACCOUNTING |
| BCH Formal | Stage03 | 31点、公式、停止条件 | 缺点/NaN/Inf失败 | PASS_BCH_FORMAL_GRID |
| 86图重绘 | Stage04 | 图/数据/manifest/readme | 零值替换/插值失败 | PASS_STAGE11_PLOT_MANIFESTS |
| CC 整理 | Stage05 | 哈希与字段复核 | 修改源 CSV 失败 | PASS_CC_RESULT_INTEGRATION |
| LDPC 整理 | Stage06 | N560/32iter/alpha复核 | 出现10/20/30已完成声明失败 | PASS_LDPC_N560_RESULT_INTEGRATION |
| 最终集成 | Stage08 | SHA256、报告、已知问题 | 任一上游 Gate 失败 | PASS_S6_FINAL_REPORT |

## Gate

Stage01 Gate：范围、配置、schema 和禁止事项全部明确，且当前分支不是 main。
