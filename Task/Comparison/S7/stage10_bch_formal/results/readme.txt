阶段名称：stage10_bch_formal
实验目的：执行 S7 配对停止 Formal 网格。
主要输入：31 Es/N0、3 突发比例、6 位置、4 配置。
完成内容：Formal CSV 与 checkpoint。
主要输出：formal_results.csv、checkpoint.bin、checkpoint_manifest.json。
当前结论：formal checker 已验证 2232 行、558 组，Gate=PASS。
已知问题：CPU 时延依赖本机环境；BCH t=1 查表对多错误模式可能误纠且无失败信号。
阶段状态：PASS
