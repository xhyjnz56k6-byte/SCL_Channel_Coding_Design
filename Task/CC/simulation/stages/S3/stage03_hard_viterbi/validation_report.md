# Stage03 验证报告

## Gate

`PASS_STAGE03_CC_HARD_VITERBI`

## Git

- 分支：`stage01-cc`
- baseCommit：`955cbb0ad2ad9e601e142b354c0405512497fdee`
- contentCommit：`b43def06a5b325790f34107751cb732a0dcb72b0`
- mergeStatus：`NOT_MERGED`

## 实际检查

| 检查 | 结果 |
|---|---|
| GNU C++ Release build | PASS |
| CTest | 1/1 PASS |
| 全零、全一、固定序列无噪声 | PASS |
| 随机 300-bit 无噪声 | 100/100 PASS |
| 单一编码 bit 翻转恢复 | PASS |
| 固定多错误确定性 | PASS |
| tie 重复运行一致 | PASS |
| 每 trellis step 归一化 | 306/306 |
| overflowCount | 0 |
| 非法长度、非二进制负向测试 | PASS |
| MATLAB `vitdec` hard | 5/5 PASS |
| codecInputMismatch | 0 |
| payloadMismatch | 0 |
| Stage02 回归 | PASS |
| `git diff --check` | PASS |

证据位于 `results/stage03_hard_viterbi_test_summary.csv` 和 `results/stage03_hard_viterbi_matlab_comparison.csv`。

本阶段未实现打孔、软判决或 AWGN，未把这些测试标记为 PASS。远程验证延后到 Stage15 后统一 push；未合并 `main`。
