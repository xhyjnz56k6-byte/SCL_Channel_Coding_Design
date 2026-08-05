阶段名称：stage11_cc_formal
实验目的：执行 S7 CC 配对停止 Formal 网格。
主要输入：31 个 Es/N0、3 个突发比例、6 个位置、4 个配置。
完成内容：2232 行结果、558 个配对比较组；帧数范围 1000～48014，无配置达到 50000 帧上限。
主要输出：formal_results.csv、checkpoint.bin、checkpoint.bin.prev、checkpoint_manifest.json、formal_validation.json。
结果绝对路径：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage11_cc_formal\results\formal_results.csv
当前结论：Formal checker PASS；原始 CSV 中无 BER/FER 零值行，未写入伪小值或零错上界。
已知问题：CPU 时延依赖本机环境；推荐工程配置对比不是纯方法差异。
阶段状态：PASS

