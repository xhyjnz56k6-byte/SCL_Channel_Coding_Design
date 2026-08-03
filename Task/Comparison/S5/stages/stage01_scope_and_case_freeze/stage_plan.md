# Stage01：范围与 Case 冻结

目标：冻结四个完整块 Soft Float/NMS 方案、两组公平比较关系、Es/N0 语义和批次分支边界。非目标：不改动 CC、LDPC、BCH、Common，不运行 Formal。

允许范围：`Task/Comparison/S5/`。禁止范围：`Task/CC/`、`Task/LDPC/`、`Task/BCH/`、`Task/Common/`。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 四个代表 Case | `s5.hpp/s5.cpp` | 长度、码率、alpha | 未知 Case 拒绝 | 全字段与 S3/S4 一致 |
| 批次分支 | 本文件及 manifest | 分支为 S5-Compare | main 拒绝 | `PASS_S5_SCOPE` |
| Es/N0 语义 | frozen config | 公式定值 | 非有限值拒绝 | 无 Eb/Es 混用 |

Gate：`PASS_S5_SCOPE`。
