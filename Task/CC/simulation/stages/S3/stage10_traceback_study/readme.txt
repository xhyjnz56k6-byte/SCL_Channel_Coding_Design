一、阶段名称
Stage10 有限回溯复核

二、实验目的
围绕 CC S3 300 bit 高速电文场景，给出可审计的 BER、FER、有效吞吐、译码时延、内存和复杂度数据。

三、实验背景和它在 S3 总任务中的作用
本阶段属于 S3 正式实验链条的一部分。Stage09 提供整块基线，Stage10/11 提供回溯和量化补充，Stage13 提供真滑窗参数控制变量，Stage14 提供时隙连续组织比较，Stage15 汇总为最终方案矩阵。

四、实验输入
payloadBits=300，SNR = Es/N0，范围 -5.0 dB 到 10.0 dB，步长 0.5 dB。

五、编码参数
卷积码 K=7，生成多项式 171/133 octal，母码率 1/2，打孔码率 R12/R23/R34。

六、译码方式
整块实验使用完整 Viterbi；滑窗和时隙实验使用已修复的真滑窗/在线到达机制；量化实验比较 Float 与 Q 位宽软判决。

七、控制变量
本阶段记录 21 个配置组合。Stage13 本轮严格区分 W、S、D 单变量变化，其它阶段保持各自冻结配置。

八、SNR范围与停止条件
正式网格使用 minFrames=1000、targetFrameErrors=200、maxFrames=50000；停止原因只允许达到目标误帧或最大帧数。

九、随机性和公平性
同一码率、SNR 和 frameIndex 共享 payload 与标准高斯母噪声；Hard/Soft 和候选参数只派生不同译码输入，不重新生成独立噪声。

十、执行流程
本轮先归档旧 results，再运行无噪声回归、Stage13 full W/S/D formal shard、后处理、Stage15 集成和 checker。

十一、输出文件
主要输出位于 results/，包括正式 CSV、figure-data CSV、PNG、plot manifest 和 Markdown 分析。

十二、主要结果
当前正式结果行数 63，累计仿真帧数 215831。

十三、结果解释
Dtb=35/49/70/84/98/112 的有限回溯数据继续用于内存-可靠性权衡。

十四、与上一轮相比的修改
20260730 本轮新增 archive/v02_20260730_before_cc_s3_formal_continuation，并把 Stage13 full W/S/D 正式网格纳入最终集成。

十五、当前进展状态
已完成本轮归档、Stage13 full W/S/D formal、Stage15 矩阵重建和基础 checker。

十六、已知限制
当前仿真是符号级离散 BPSK-AWGN；没有显式采样率、过采样、脉冲成形、匹配滤波、带宽和连续波形噪声建模。

十七、是否通过 Gate
本轮阶段级 checker 已通过；最终 Gate 仍需 Git 审计、提交和远程验证后确认。
