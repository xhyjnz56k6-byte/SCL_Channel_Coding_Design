# Stage01 CC 参数契约冻结计划

## Stage

`stage01_cc_contract`

## 目标

冻结后续 CC S3 实验共同使用的数学定义、位序、状态编号、度量、打孔接口、结果字段、检查点语义、命名规则和 Stage 依赖关系。

## 非目标

- 不实现 trellis、编码器或 Viterbi 译码器。
- 不选择最终 2/3、3/4 打孔图样。
- 不运行 AWGN 性能仿真或生成性能曲线。
- 不修改 `Task/Common`、`Task/BCH` 或 `Task/LDPC`。

## 允许范围

仅允许新增或修改：

```text
Task/CC/simulation/stages/S3/stage01_cc_contract/**
```

## 禁止范围

```text
Task/BCH/**
Task/LDPC/**
Task/Common/**
其他既有 Stage 和用户文件
```

## 接口与数据格式

- 机器可读合同：`config/cc_contract.json`
- 机器可读结果 schema：`config/cc_result_schema.json`
- 冻结参数表：`frozen_config.csv`
- 人工说明：`cc_contract.md`、`cc_bit_order.md`、`cc_metric_definition.md`、`cc_result_schema.md`
- 自动检查：`scripts/check_stage01_contract.py`

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| K=7、64 状态、171/133 和零尾长度冻结 | `config/cc_contract.json` | 精确字段和值检查 | 修改状态数或多项式后必须失败 | 参数一致 |
| MATLAB 位序和状态转移冻结 | `cc_bit_order.md`、合同 JSON | 已知转移向量检查 | 反转寄存器方向必须失败 | 64×2 定义唯一 |
| 硬/软度量、tie-break 和归一化冻结 | `cc_metric_definition.md`、合同 JSON | 公式和策略检查 | 缺失位作为硬 0 必须失败 | 度量语义完整 |
| 长度、actualRate 和 SNR 公式冻结 | `cc_contract.md`、`frozen_config.csv` | 300/612 及逐点公式检查 | 使用理论 1/2 替代实际码率必须失败 | 数学关系一致 |
| CSV/JSON、checkpoint 和命名冻结 | `cc_result_schema.md`、schema JSON | 必需字段和枚举检查 | 删除必需字段必须失败 | schema 完整 |
| Stage 依赖关系冻结 | `cc_dependency_graph.md` | 依赖顺序检查 | 缺失或逆序依赖必须失败 | Stage01～15 全覆盖 |

## Gate

只有以下检查全部实际通过，才允许声明：

```text
PASS_STAGE01_CC_CONTRACT
```

- checker 正向检查通过；
- checker 内置负向变异检查全部被拒绝；
- `git diff --check` 通过；
- 修改范围未越过 Stage01；
- 审计记录与实际 Git 状态一致。

## 目录说明

本 Stage 属于规格冻结，不含 C++ 生产实现。`include/`、`src/`、`matlab/` 和 `results/` 保留用途说明文件，避免用空目录或 `.gitkeep` 冒充内容。
