# Stage01 文件变更说明

## 功能范围

功能提交 `df295c90a18d43762c6154b76d97b6f28d524062` 相对基线 `0680b6f4ae00e2c6b1fbe2acecc05d5875e8bfda` 新增 18 个文件，全部位于：

```text
Task/CC/simulation/stages/S3/stage01_cc_contract/
```

主要内容：

- `cc_contract.md`：长度、码率、SNR、随机公平性、BER/FER 和停止规则；
- `cc_bit_order.md`：171/133 展开、寄存器方向、state index 和输出顺序；
- `cc_metric_definition.md`：hard/soft 度量、tie-breaking、归一化和去打孔中性语义；
- `cc_result_schema.md`：结果、checkpoint/resume、shard/merge 和绘图命名；
- `cc_dependency_graph.md`：Stage01～Stage15 依赖和 Gate 顺序；
- `config/*.json`、`frozen_config.csv`：机器可读合同；
- `scripts/`、`tests/`：正向及负向自动检查；
- `results/`：实际 checker 输出。

## 审计范围

审计提交只增加 `manifest.json`、`validation_report.md`、`changed_files.md`、`changes.patch`、`git_commit.txt` 和审计 checker，不改变冻结的功能合同。

## 越界情况

未修改 `Task/Common/**`、`Task/BCH/**`、`Task/LDPC/**` 或其他 Stage。
