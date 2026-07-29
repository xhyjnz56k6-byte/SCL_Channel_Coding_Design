阶段名称：软信息量化
实验目的：支撑卷积码 CC S3 的 软信息量化 验证。
Stage11 研究的是：
	软判决 Viterbi 中，接收端的“软信息”到底需要保留多少 bit 精度，才能既接近浮点软判决性能，又减少存储和实现复杂度。
主要参数：payloadLength=300 bit；Float/Q3/Q4/Q6。
完成内容：保留既有实现，并按本轮要求补充审计、结果或图。
主要输出：stage_plan.md、manifest.json、validation_report.md、known_issues.md 和 results。
当前结论：以 validation_report.md 和本轮结果 CSV 为准，不使用未验证数据。
已知问题：Stage09 完整 -5..10 dB 粗网格尚需继续正式补跑。
阶段状态：PASS
