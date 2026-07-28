# Stage05 验证报告

Gate：`PASS_STAGE05_CC_MATLAB_REFERENCE`

- 分支：`stage01-cc`
- baseCommit：`90a256337ef5cb86148fd11d934f3e38b34ab2bb`
- contentCommit：`47057c4293a415f054675f8c63d7a94e3451b047`
- mergeStatus：`NOT_MERGED`

实际执行结果：

| 检查 | 结果 |
|---|---|
| C++ Release reference runner | PASS |
| `poly2trellis` nextStates/outputs | 128/128 PASS |
| `convenc` 编码、尾部、最终状态 | 16/16 PASS |
| `vitdec` hard | 16/16 PASS |
| `vitdec` unquant receivedSymbols | 16/16 PASS |
| `vitdec` unquant fixed LLR | 16/16 PASS |
| C++/MATLAB total bit mismatch | 0 |
| reference asset SHA256 | 3/3 已保存并可复算 |
| `git diff --check` | PASS |

首次后置 checker 因 MATLAB table 默认列名而拒绝结果；显式冻结七个输出列名后重新运行 MATLAB 和 Python checker，全部通过。未修改向量数值。

证据：`results/stage05_matlab_reference_comparison.csv`、`stage05_matlab_reference_hashes.json`、`stage05_matlab_reference_test_summary.csv`。

本阶段未对打孔图样或 AWGN 性能作结论。远程分支 `origin/stage01-cc` 已验证包含本 Stage 功能提交；未合并 `main`。
