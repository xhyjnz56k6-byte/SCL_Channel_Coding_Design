# Stage12 已知连续擦除卷积码独立验证：规格冻结

## 目标

在不重跑 Stage10 Formal、不修改其合并 CSV 的前提下，独立验证 CC R2/3 在 5% 已知连续擦除下 FER 接近 1 是否可复现；同时以 MATLAB 官方卷积码函数交叉验证，并以最小块交织诊断解释机制。仅当 Stage12 Gate 为 PASS，才可归档旧 Stage11、重绘中文图并生成 20 张 Aggregate 图。

## 非目标

- 不重跑六信道 Formal、全量 Grid Smoke 或任何新 Formal 数据。
- 不修改 `Task/Comparison/S5/results/formal/merged/formal_merged_results.csv`。
- 不修改 `Task/BCH/`、`Task/CC/`、`Task/LDPC/`、`Task/Common/`。
- 交织仅作诊断，不写入 Stage10、方案推荐或 S7 结论。

## 已冻结前提

- 分支：`S5-Compare`；开始时 HEAD/远端：`70572ad999f17339fb4a4a3d4b0fbfbda6dd168f`。
- Formal CSV SHA-256：`dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947`。
- 既有 Stage11：86/86 图通过，且该哈希与绘图审计记录一致。
- CC R2/3 发送长度为 459；擦除长度定义为 `round(fraction*Ntx)`，已知擦除 LLR 固定为 0。

## 范围与接口

- 新增范围：`Task/Comparison/S5/stages/stage12_known_erasure_cc_validation/`（独立 C++、MATLAB、trace、比较和审计记录）。
- 允许后续修改：`Task/Comparison/S5/current/`、`Task/Comparison/S5/stages/`、`Task/Comparison/S5/results/stage11/`、`Task/Comparison/S5/results/Aggregate/`、`Task/Comparison/S5/archive/`、`Task/Comparison/S5/*.md`。
- Stage12 C++ 与 MATLAB 均独立产生 payload、编码、打孔、BPSK、擦除、软度量、去打孔与译码；MATLAB 不读取任何 C++ 中间结果或 BER/FER。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 参数与链路可审计 | `stage12/.../stage12_parameter_audit.md` | 审核 payload、K=7、171/133、尾比特、打孔、LLR、擦除索引 | 不允许把 459 个发送符号误作 612 个母码位 | 参数全量可追溯 |
| C++ 固定帧 trace | `stage12/cpp/traces/` | R2/3：帧 0、1；R1/2：帧 0；0%、5%，无噪声/4/8 dB | 检查 LLR=0 不偏置分支度量 | trace 可解释 payload 错误形态 |
| C++ 最小比例扫描 | `stage12/cpp/results/` | R2/3：0/1/2/3/5% × 0/4/8/10 dB；1000/200/10000 | NaN、Inf、非法停止或计数不可复算即失败 | 5% 于 4、8、10 dB 复现 FER≥0.99 |
| MATLAB 官方独立验证 | `stage12/matlab/` | `poly2trellis`/`convenc`/`vitdec`；0%、5% × 0/4/8/10 dB | 禁读 C++ 中间和统计输出 | 无损逐 bit 一致；5% 呈同类严重 FER 平台 |
| 块交织诊断 | `stage12/cpp/results/` | 17×27 覆盖全部 459 个发送符号；无噪声无擦除逐 bit 恢复 | 禁止截断、填充、部分交织；不允许纳入 Stage10 或推荐 | 仅 `diagnostic_only` |
| C++/MATLAB 汇总 | `stage12/comparison/` | 置信区间、趋势、FER 平台与 trace 比较 | 不能要求独立随机序列逐帧一致 | 无实现错误且结论支持 Stage10 |
| Stage11 中文重绘（仅 Stage12 PASS 后） | `results/stage11/` | 86 图、同 Formal hash、中文字体检查、零值不替换 | 无中文可用字体则 BLOCKED | `PASS_S5_STAGE11_CHINESE_REPLOT` |
| Aggregate 图 | `results/Aggregate/` | 20 图，源为 Formal CSV、指标与曲线数正确 | 禁插值生成曲线点和混入 Stage12 数据 | `PASS_S5_AGGREGATE_PLOT_AUDIT` |

## 串行 Gate

1. 首先运行且只运行 Stage12。
2. 若发现可使 Stage10 5% 擦除结论失效的实现错误：保留证据并停止，状态为 `BLOCKED_STAGE12_KNOWN_ERASURE_CC_VALIDATION`。
3. 若 MATLAB 统计不足：状态为 `PARTIAL_PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION`，停止且不得重绘。
4. 仅 `PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION` 才进入旧图归档、中文重绘和 Aggregate。
5. 最终依次要求 Stage12、中文重绘、Aggregate、最终集成全部 PASS；本轮不 commit、push 或 merge。

## 批准后修正（2026-08-03）

- R2/3 块交织器冻结为 17×27，恰好覆盖全部 459 个实际发送符号；禁止截断、填充或仅交织部分符号。
- 固定向量审计共享原始 payload，但 C++ 与 MATLAB 独立编码、打孔、译码；母码、发送位、无噪声 payload 必须逐 bit 一致。
- 独立统计验证使用彼此独立的 payload seed 和 AWGN seed，只比较 BER、FER、95% 置信区间与趋势。
- R2/3 固定 trace 总数保持两帧；先审计 frame 0、1 的擦除起点，若过近则改用 frame 0、31。
- MATLAB 高 SNR 平台 Gate：`FER >= 0.99`，或 `FER >= 0.98` 且与 C++ 95% FER 置信区间重叠。
