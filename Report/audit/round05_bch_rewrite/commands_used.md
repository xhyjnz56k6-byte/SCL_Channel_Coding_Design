# 主要命令记录

```powershell
python Report/scripts/build_chapter04_bch_assets.py
latexmk -g -xelatex -interaction=nonstopmode -file-line-error main.tex
pdftoppm -f 34 -l 48 -png -r 110 Report/main.pdf round05c_ch4
git diff --name-only -- Task/BCH Task/Common
git status --short
```

全量构建实际执行多于两次；最终一次日志用于结论判定。PDF渲染页覆盖报告第33至47页。
