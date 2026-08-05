阶段名称：
stage00_repository_audit

实验目的：
确认 S7 分支、工作区、目录边界、依赖源码、历史结果和执行环境，为后续 Stage 提供可追溯起点。

主要输入：
Git HEAD d01b366ea84d38cc73c7b11cc9a7534446987ac2、根目录 AGENTS.md、初始规划/S7-Plan.md、S5/S6 报告与现有 BCH/CC/Common 源码。

完成内容：
已执行仓库根目录、分支、HEAD、工作区、main 差异、S7 目录、Python/CMake 和历史 LDPC 来源检查。

主要输出：
repository_audit.md、stage_plan.md、manifest.json、validation_report.md、known_issues.md。

当前结论：
允许在用户指定的 S7-Comparision 分支创建 Task/Comparison/S7；既有编码目录保持只读。

已知问题：
分支名不符合建议格式；历史存在已跟踪构建产物；MATLAB 可用性尚需在 Stage08 前实测。

阶段状态：
PASS

