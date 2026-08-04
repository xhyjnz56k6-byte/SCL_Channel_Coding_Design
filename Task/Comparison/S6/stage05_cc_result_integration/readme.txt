阶段名称：stage05_cc_result_integration

实验目的：整合 R1/2 卷积码整块与时隙 Hard/Float Soft 历史正式结果。
主要输入：Stage14 all-decisions Formal CSV，K=300、N=612、D=70/W=128/S=25（时隙）。
完成内容：已从单一 Stage14 Formal 源整合 8 个方案并运行 checker。
主要输出：cc_integrated_results.csv、cc_source_inventory.csv、cc_integration_summary.json。
当前结论：8 个方案各 31 点，共 248 行，Gate 通过；未重跑 CC Formal。
已知问题：历史停止不是严格 pair-stop；CPU 时间与实时决策时延不可混用。
阶段状态：PASS
