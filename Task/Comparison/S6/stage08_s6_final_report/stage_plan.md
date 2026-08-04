# Stage08 最终报告计划

核验仓库范围、归档、readme、BCH/CC/LDPC 数据、112 张图、环境、SHA256 和 Git 状态；全部通过后生成最终中文报告，不 commit、不 push、不 merge。

| 需求 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|
| 数据完整 | 行数/字段/有限值 | 缺行阻断 | PASS |
| 图完整 | 86+26 图目录 | 缺文件阻断 | PASS |
| readme | S6 全目录扫描 | 任一缺失阻断 | PASS |
| 归档 | manifest 哈希复算 | mismatch 阻断 | PASS |
| 最终 SHA | 全发布文件哈希 | 缺失阻断 | PASS |
