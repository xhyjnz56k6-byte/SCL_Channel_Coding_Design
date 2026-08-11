# Round08-B 验证报告

## 结果

功能 Gate：`PASS_ROUND08_B_S5_CHAPTER7_FORMAL_WRITING`

## 实际执行的验证

- Round08-A 扫描重建：`python Task/Comparison/S5/report_scan_round08A/round08a_scan.py --overwrite`，结果 `PASS rows=744 stage11=86 aggregate=20`；
- FER 插值一致性：Round08-A 证据矩阵与权威 Stage11 对数域 FER 插值逐项比较，结果 `PASS_ROUND08A_LOG_FER_INTERPOLATION_ALIGNMENT`；
- XeLaTeX：在 `Report/` 执行 `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`，成功生成 124 页 `main.pdf`；
- 编译日志：未发现 fatal error、未定义引用、未定义文献或 overfull box；
- 章节页数：目录中第7章起始页93，第8章起始页107，第7章共14页；
- 正文统计：6071个中文字符、8个一级节、5个小节；
- 图表统计：22张正式结果子图、14个正文图号、8张三线表、3个 Visio 占位；
- 引用完整性：23个标签、16次图表引用，无缺失标签；22个图片路径均存在；
- 图片一致性：22张报告 PNG 的 SHA-256 均与 Stage11/Aggregate 正式源图匹配；
- PDF 视觉检查：将第7章14页逐页渲染并检查，未发现裁切、横向溢出、空白页、图表重叠或不可辨识占位；
- 语言检查：正文未出现开发日志或写作元叙事；源码中 `round08b` 仅存在于内部图片路径；
- 数据边界检查：N/A 保留，未作范围外外推，未平滑或拟合曲线，未制造 error floor；
- 参数复核：N480/N640 的归一化系数分别为0.95/0.80，最大迭代次数32，卷积码与LDPC近码率配对正确。

## 未执行事项

- 未重新运行 Formal；
- 未修改或重绘正式实验数据；
- 未执行 commit、push 或 `main` 合并。
