阶段：Stage12 - 连续编码与时隙组织基础

目的：实现 300 bit 电文的连续编码状态和打孔相位跨时隙保持，为实时发送场景建立发端基础。

作用：覆盖整块 300、50x6、100x3、150x2 四种组织，确保拆分时隙后与整块连续传输的比特流一致，并可从 checkpoint 恢复。

得到的结果：三种码率、四种组织、每 Case 100 帧均通过状态、相位、尾部和恢复回归；连续流与整块流一致，Gate 为 PASS_STAGE12_CONTINUOUS_ENCODER。

主要程序：src/continuous_encoder.cpp 是连续状态编码核心；scripts/run_stage12.py 是测试入口；results/stage12_slot_metadata.csv 给出四种时隙组织元数据。

交付关系：这是 Stage14 在线时隙比较的前置正确性证明；其结果本身不需作为最终性能结果上传。
