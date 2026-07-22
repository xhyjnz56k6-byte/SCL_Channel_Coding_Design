# BCH-04 验证报告

| 检查 | 结果 | 证据 |
|---|---|---|
| MinGW CMake configure | PASS | `Task/BCH/segmented/build/bch04` 已生成 |
| Release build | PASS | 三个 BCH 测试目标构建成功 |
| CTest | PASS | `bch15_encoder`、`bch15_syndrome_table`、`bch15_lookup_decoder` 均通过 |
| 无错穷举 | PASS | 2048/2048；所有无错 mismatch 为 0 |
| 单错穷举 | PASS | 30720/30720；payload、位置、post syndrome、lookup miss 均为 0 |
| 双错全集 | PASS | 215040/215040；全部误纠至另一合法码字，原 payload 恢复 0 |
| 固定多错 seed | PASS | 12 seed x 4 message = 48 行 |
| 非法输入与损坏表 | PASS | 14/16/非 bit 输入拒绝；缺失、错误及 15/100 越界条目均覆盖 |
| CSV 审计脚本 | PASS | `PASS_BCH04_LOOKUP_DECODER_AUDIT_CSV` |
| git diff --check | PASS | 无空白错误 |
| Task/Common 范围 | PASS | BCH-04 功能范围无 Common 文件 |

## Common 六项二进制回归

| 程序 | Exit code | 结果 |
|---|---:|---|
| `Task/Common/build/stage04/test_common04_random_policy.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_gaussian_noise.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_modulation_awgn.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_metrics_control.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_checkpoint.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_integration.exe` | 0 | PASS |

`functionalGate=PASS`。审计提交和远程验证完成后，以 `auditGate=PASS`、`finalGate=PASS_BCH04_LOOKUP_DECODER_MISCORRECTION_AUDIT` 记录最终状态。
