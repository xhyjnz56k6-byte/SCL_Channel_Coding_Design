# Stage02 验证报告

## 结论

```text
PASS_STAGE02_CC_TRELLIS_ENCODER
```

## Git 边界

| 项目 | 值 |
|---|---|
| 分支 | `stage01-cc` |
| baseCommit | `1cace054f06c0648bd6b2593c1b2430b92fd3d5f` |
| contentCommit | `4b268e385eda34c79352ca186a57985b7d93869a` |
| repairCommit | `b79749d6b4e6fc5ef97ade3ac226078494e834f2` |
| mergeStatus | `NOT_MERGED` |

## 实际执行

| 检查 | 规模 | 结果 |
|---|---:|---|
| GNU C++ Release build | 2 源文件、1 测试程序 | PASS |
| CTest | 1/1 | PASS |
| trellis 全状态遍历 | 64×2 分支 | PASS |
| 全零、全一、单位脉冲、固定序列 | 5 类 | PASS |
| 随机 300-bit 零尾 | 100 帧 | PASS |
| 200-bit 兼容性 | 1 组 | PASS |
| 分段拼接与一次编码 | 300 bit、3 段 | PASS |
| 非二进制输入负向测试 | 1 组 | PASS |
| 输出长度 | 300+6 输入、612 输出 | PASS |
| 零尾终止状态 | state 0 | PASS |
| MATLAB `poly2trellis` | 128 分支 | PASS，next/output mismatch=0 |
| MATLAB `convenc` | 4 固定向量 | PASS，bit mismatch=0 |
| `git diff --check` | 当前功能差异 | PASS |

## MATLAB 失败与修复记录

首次 MATLAB 执行把 CSV 二进制串自动推断为数值，`convenc` 因输入类型/前导零丢失而拒绝。修复为使用 `detectImportOptions` 并强制 `inputBits`、`cppMotherBits` 为 string 后重跑，随后完整 trellis 和固定向量对比均通过。没有修改 C++ 数据来掩盖失败。

审计前复跑还发现 build/test 脚本会重写摘要并删去已存在的 MATLAB Gate 行。修复提交改为读取两份 MATLAB CSV，逐行验证 4 个向量、128 条分支及所有 mismatch，再稳定写入最终 Gate。修复后重新执行 build、CTest 和摘要检查通过。

## 证据

- `results/stage02_trellis_encoder_test_summary.csv`
- `results/stage02_trellis_encoder_matlab_comparison.csv`
- `results/stage02_trellis_encoder_matlab_trellis_comparison.csv`
- `results/stage02_trellis_encoder_cpp_trellis.csv`

## 未执行

本阶段未实现或运行 Viterbi、打孔、AWGN smoke/prescan/formal；这些项目没有标记为 PASS。

批次远程验证按用户要求在 Stage15 后统一执行。当前未合并 `main`。
