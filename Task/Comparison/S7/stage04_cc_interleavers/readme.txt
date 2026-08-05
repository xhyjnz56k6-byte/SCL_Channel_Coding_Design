阶段名称：stage04_cc_interleavers
实验目的：实现按 trellis step 组织且保持母码输出对的 CC 交织器。
主要输入：306 trellis steps、612 coded bits、depth=4/8/16、伪随机 span=32/64/128。
完成内容：NONE、SHORT_DEPTH_BLOCK、PSEUDORANDOM、尾窗口、正逆映射和 pair Gate。
主要输出：s7_core 和单元测试结果。
当前结论：编译与单元测试通过。
已知问题：物理时间不可由 span 推导。
阶段状态：PASS

