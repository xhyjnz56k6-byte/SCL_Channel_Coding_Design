# Stage04 验证报告

Gate：`PASS_STAGE04_CC_SOFT_VITERBI`

- 分支：`stage01-cc`
- baseCommit：`b708dafdc13ac65faddcc3821a62a2f1238d5375`
- contentCommit：`52a679b1879210024a7d3c17fcdda0a9638b934d`
- mergeStatus：`NOT_MERGED`

| 检查 | 结果 |
|---|---|
| GNU C++ Release build | PASS |
| CTest | 1/1 PASS |
| 无噪声/固定低噪声 300-bit | 100/100 PASS |
| hard/soft 同 receivedSymbols | PASS |
| 306 次逐步归一化 | PASS |
| nonFiniteMetricCount | 0 |
| NaN/Inf 负向测试 | PASS |
| MATLAB terminated unquantized `vitdec` | 3/3 PASS |
| codecInputMismatch/payloadMismatch | 0/0 |
| Stage03 回归 | PASS |
| `git diff --check` | PASS |

首次 MATLAB 导入因内层分号被误判为外层 delimiter 而失败；固定外层 delimiter 为逗号后重新运行通过。失败发生在数据导入阶段，没有修改 C++ 向量或参考结果。

未执行打孔、量化或 AWGN 性能实验。远程验证延后到 Stage15 统一 push；未合并 `main`。
