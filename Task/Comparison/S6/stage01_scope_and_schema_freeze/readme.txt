阶段名称：
stage01_scope_and_schema_freeze

实验目的：
冻结 S6 范围、统一信道、正式网格、结果字段、Gate 和禁止事项。

主要输入：
BCH S200/B200、CC R1/2 Block/Slot、LDPC Direct BG2 N560 历史配置与审计证据。

完成内容：
冻结范围、schema、验收矩阵和配置。

主要输出：
stage_plan.md、frozen_config.csv、result_schema.csv、manifest.json、validation_report.md、known_issues.md。

当前结论：
S6 主范围已冻结；只有 BCH 运行新 Formal，CC/LDPC 复用历史结果。

已知问题：
不自动 commit，因此最终 functional range 只能在用户授权提交后闭合。

阶段状态：
PASS
