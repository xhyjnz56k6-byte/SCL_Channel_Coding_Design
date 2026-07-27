# stage12 固定绝对遮挡长度实验 C 验证报告

## 结论

功能 Gate：**PASS**。

实验按 `L=5、10、20、30` 个调制符号执行，覆盖 K200 与 K300 各 4 个 BCH 案例，共 32 个正式点。
所有点均严格满足请求长度、合法非环绕随机起点、整数统计一致性及 `5000/200/50000` 停止规则。

## 实际执行

| 检查 | 结果 |
|---|---|
| CMake Release 配置与编译 | PASS |
| CTest CLI 负向测试 | PASS，1/1 |
| 32 点正式仿真 | PASS |
| 实验 C checker | `PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_C_FIXED_LENGTH` |
| 原 stage12 checker 回归 | `PASS_STAGE12_BLOCKAGE_FORMAL` |
| 6 张 PNG、figure-data 与 SHA-256 manifest | PASS |
| K200 FER 图人工检查 | PASS |
| K300 误纠率图人工检查 | PASS |

## 结果摘要

- 固定长度增加时，8 个案例的 BER/FER 总体显著上升。
- S15 分块方案在 `L=5` 时已出现较高 FER；其误纠率与 FER 相同，符合该译码路径的成功上报语义。
- 385 整块方案在较短遮挡下最稳健：K200 的 `L=5`、K300 的 `L=5/10` 均为零观测 FER，均已运行至 50000 帧上限。
- `L=30` 时所有方案均明显退化；K200/K300 的 S15 FER 均达到 1。

## 审计说明

原始零值未被改写。PNG 对数纵轴中的零观测点只在绘图数据的 `plotValue` 字段使用可追踪替代值。
checkpoint 属于正式仿真中间资产，不进入 Git。
