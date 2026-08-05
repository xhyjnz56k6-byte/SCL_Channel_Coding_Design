阶段名称：stage13_latency_complexity
实验目的：从 Stage10/11 Formal 原始 CSV 汇总译码、交织、解交织 CPU 时间和结构缓冲代价。
主要输入：BCH/CC Formal CSV，共 4464 行。
完成内容：已生成 8 配置汇总并通过独立 checker。
主要输出：latency_complexity_summary.csv、stage13_validation.json。
当前结论：T_add_cpu 恒等于交织与解交织 CPU 均值之和；结构等待量未换算为物理时间。
已知问题：CPU 时间依赖本机；全局精确分位数不能由点级分位数重建。
阶段状态：PASS
