阶段名称：真滑窗 Viterbi
实验目的：支撑卷积码 CC S3 的 真滑窗 Viterbi 验证。
	卷积码接收数据连续到来时，译码器应该每次看多长的一段数据、每次向前移动多少、回溯多深，才能在纠错性能、输出速度和内存之间取得平衡？
		这里有三个关键参数：
		W：窗口长度 Window
		S：滑动步长 Slide
		D：回溯深度 Traceback Depth
主要参数：payloadLength=300 bit；W/S/D 参数扫描。
完成内容：保留既有实现，并按本轮要求补充审计、结果或图。
主要输出：stage_plan.md、manifest.json、validation_report.md、known_issues.md 和 results。
当前结论：以 validation_report.md 和本轮结果 CSV 为准，不使用未验证数据。
已知问题：Stage09 完整 -5..10 dB 粗网格尚需继续正式补跑。
阶段状态：PASS
