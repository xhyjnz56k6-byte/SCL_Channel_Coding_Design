# 报告工作区

本目录用于技术报告的资料扫描、证据索引和 LaTeX 骨架，不是实验结果目录。本报告不含摘要和绪论；当前阶段只建立资料基础，正文尚未冻结。

使用 XeLaTeX 编译：`latexmk -xelatex main.tex`。将人工制作的 Visio PNG 放在 `figures/visio/` 对应子目录；已有实验图保持在原位置并仅由 evidence 索引引用。图不存在时 `\reportfigure` 显示占位框。

`evidence/` 保存扫描结果与差异登记。可运行 `python scripts/scan_repository.py` 更新台账；脚本只写入本目录，不应修改原始实验结果。
