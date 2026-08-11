# 第7章版式前后对比

| 项目 | Round08-B | Round08-C |
|---|---|---|
| 正文行距 | 第7章局部 `\linespread{0.94}\selectfont` | 删除局部行距覆盖，恢复 `ctexrep` 全报告默认正文行距 |
| 浮动间距 | 第7章局部 `\textfloatsep`、`\floatsep`、`\intextsep` 均为 8pt | 删除局部压缩，恢复全报告默认浮动间距 |
| 普通双图显示宽度 | `0.49\textwidth` minipage 内 `0.84\linewidth`，有效宽约 `0.412\textwidth` | `0.49\textwidth` minipage 内 `0.98\linewidth`，有效宽约 `0.480\textwidth` |
| 高信息密度组合图 | 左右并排，有效宽约 `0.412\textwidth` | 上下排列，`0.90\textwidth` minipage 内 `0.98\linewidth`，有效宽约 `0.882\textwidth` |
| 图表题 | 使用全局默认 caption 字号 | 第7章局部 `\captionsetup{font=small,labelfont=normalfont,skip=0.6em}` |
| Visio占位高度 | `0.14\textheight` | `0.18\textheight`，与既有报告占位尺度一致 |
| 第7章页数 | 14页（93--106） | 24页（94--117） |

第4～6章没有局部 `\linespread`、`\setstretch`、`\baselineskip` 或局部浮动间距压缩。Round08-C 因此不设置新的正文行距，只移除第7章独有的紧缩设置。
