# Stage01 验证报告

## 结论

```text
PASS_STAGE01_CC_CONTRACT
```

Stage01 功能合同、机器可读 schema、正向检查和负向变异检查均通过。该 Gate 只表示规格冻结通过，不表示 trellis、编码器、Viterbi、MATLAB 对比或 AWGN 性能已经实现。

## 环境

| 项目 | 实际值 |
|---|---|
| 仓库 | `C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design_CC` |
| 分支 | `stage01-cc` |
| 基线提交 | `0680b6f4ae00e2c6b1fbe2acecc05d5875e8bfda` |
| 功能提交 | `df295c90a18d43762c6154b76d97b6f28d524062` |
| Python | 当前工作区 `python` |

## 实际执行结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 正向合同校验 | PASS | 所有冻结不变量一致 |
| 错误 stateCount 负向变异 | PASS | 非法合同被拒绝 |
| 生成多项式 bit 反转负向变异 | PASS | 非法合同被拒绝 |
| 使用理论 1/2 代替 actualRate | PASS | 非法合同被拒绝 |
| 打孔缺失 hard bit 当 0 | PASS | 非法合同被拒绝 |
| 删除 sigmaSquared 字段 | PASS | 非法 schema 被拒绝 |
| 必需文档检查 | PASS | 7 个核心文档/配置全部存在 |
| `git diff --check` | PASS | 返回码 0，无输出 |
| 修改范围检查 | PASS | 功能 diff 的 18 个文件全部位于 Stage01 |

原始 checker 结果：

```text
results/stage01_cc_contract_check_results.csv
```

## 未执行项目

- MATLAB 未执行：本阶段只冻结对齐约定，实际 `poly2trellis`/`convenc` 对比属于 Stage02～Stage05。
- C++ build/unit test 未执行：本阶段无 C++ 生产源码。
- smoke、prescan、formal 未执行：这些属于后续 Stage，不能标记为 PASS。

## Git 和远程状态

- 功能范围由 `manifest.json` 中的 `baseCommit` 和 `contentCommit` 精确限定。
- `changes.patch` 由该真实功能范围生成，不包含审计提交自身。
- 批次远程验证按用户要求延后至 Stage15 完成后的统一 push。
- `mergeStatus` 保持 `NOT_MERGED`。
