阶段名称：整块与连续比较

实验目的：支撑卷积码 CC S3 的 整块与连续比较 验证。

Stage14 的目标是比较：

A：整块 300 bit 编码
B：50 bit × 6 个时隙连续编码
C：100 bit × 3 个时隙连续编码
D：150 bit × 2 个时隙连续编码

看它们在以下方面有什么区别：
BER、FER；
时隙边界附近的误码；
第一次输出需要等多久；
整帧什么时候完成；
有效吞吐；
连续分时隙是否真的带来实时性优势。







主要参数：payloadLength=300 bit；A/B/C/D 独立运行。
完成内容：保留既有实现，并按本轮要求补充审计、结果或图。
主要输出：stage_plan.md、manifest.json、validation_report.md、known_issues.md 和 results。
当前结论：以 validation_report.md 和本轮结果 CSV 为准，不使用未验证数据。
已知问题：Stage09 完整 -5..10 dB 粗网格尚需继续正式补跑。
阶段状态：PASS
