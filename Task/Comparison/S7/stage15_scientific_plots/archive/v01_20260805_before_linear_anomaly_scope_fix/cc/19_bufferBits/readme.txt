图名称：CC 交织缓冲量
实验目的：展示 S7 CC 的缓冲量（bit）。
固定参数：使用冻结编码、未知连续 BPSK 极性反转和 Formal/专项扫描停止规则。
改变量：见 figure_data.csv 的 series 与 x。
突发比例：由 figure_data.csv 和图名限定。
突发位置：六位置聚合或图中明确位置。
编码方案：CC 冻结方案。
交织方式：图例所列配置；CC D8 与 PSEUDO128 不解释为纯方法差异。
SNR 范围：来自原始数据，不外推。
停止规则：Stage10/11 paired stopping；Stage12 每起点 200 帧。
原始数据来源：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage13_latency_complexity\results\latency_complexity_summary.csv
数据文件名称：figure_data.csv。
数据绝对路径：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage15_scientific_plots\results\cc\19_bufferBits\figure_data.csv
历史工程数据来源：S6 LDPC 独立参考，仅记录、不混入本图。
历史数据绝对路径：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S6\results\ldpc\ldpc_n560_integrated_results.csv
绘图过滤规则：不平滑、不删除非零异常点。
零值处理规则：原始 0 保留；对数图不绘制，不替换、不延伸、不标 error floor 或上界。
主要结论：仅由可见原始点支持；参见 Stage14 推荐报告。
已知限制：CPU 时延依赖本机；强突发下 FER 可能饱和。
图状态：PASS
