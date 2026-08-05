# stage00_repository_audit 计划

目标：建立 S7 可追溯仓库起点，冻结目录和依赖边界。

非目标：修改源码、运行编译码 Smoke、运行 Formal、生成科研图。

允许范围：`Task/Comparison/S7/stage00_repository_audit/**` 及 S7 顶层规格文件。

禁止范围：所有既有编码目录、S5、S6、旧 Stage 和旧结果。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| Git 起点可追溯 | repository_audit.md | rev-parse/status/diff | main 分支或不明修改 | 分支非 main 且状态已记录 |
| 目录范围唯一 | repository_audit.md | 检查 Comparison 布局 | 同时创建 Task/S7 | 仅使用 Task/Comparison/S7 |
| 依赖可定位 | repository_audit.md | 源文件存在性检查 | 依赖缺失 | BCH/CC/Common 路径存在 |
| LDPC 限制明确 | repository_audit.md | inventory/hash/参数核对 | 混入交织排名 | 仅独立参考表 |

Gate：上述审计全部完成，且未修改范围外文件。

