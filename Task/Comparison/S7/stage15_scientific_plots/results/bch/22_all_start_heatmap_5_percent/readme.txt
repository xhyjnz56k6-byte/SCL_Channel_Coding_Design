图名称：BCH 5%突发全起点热力图
实验目的：展示全起点 FER 空间分布。
固定参数：HIGH 工作点、5% 连续极性反转、每起点 200 帧。
改变量：交织配置和突发起点。
突发比例：5%；实际突发长度 14 bit；BCH 编码后长度 285 bit。
突发位置：全部合法起点，范围 0～271。
编码方案：BCH 冻结方案。
交织方式：全部 Formal 配置。
SNR 范围：单个 HIGH 工作点。
停止规则：每起点固定 200 个共享帧。
原始数据来源：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage12_all_start_scan\results\bch\all_start_results.csv
数据文件名称：figure_data.csv。
数据绝对路径：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage15_scientific_plots\results\bch\22_all_start_heatmap_5_percent\figure_data.csv
历史工程数据来源：S6 LDPC 独立参考，仅记录、不混用。
历史数据绝对路径：C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S6\results\ldpc\ldpc_n560_integrated_results.csv
绘图过滤规则：nearest，不平滑、不删除点。
零值处理规则：线性热力图保留并显示原始零值。
主要结论：用于定位 worstStart、bestStart 和边界敏感性。10% 突发下所有起点和全部配置 FER=1，超过 BCH-S200 的结构纠错能力，因此不再用无区分度热力图展示；10% 原始数据和旧图均已归档保留。
已知限制：FER 分辨率为 0.005；不对未测起点插值。
图状态：PASS
