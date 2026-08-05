阶段名称：stage03_bch_interleavers
实验目的：实现 BCH NONE、CODEBLOCK、ROW_COLUMN、GLOBAL_PSEUDORANDOM 及公平性元数据。
主要输入：285 bit、19 个 BCH 子码字、冻结 depth/rows/seed。
完成内容：正逆映射、末组、SHA256、span/buffer/fairnessGroupId 和非法参数检查。
主要输出：s7_core 和单元测试结果。
当前结论：编译与单元测试通过。
已知问题：性能结论只来自 Stage09 小样本，不是 Formal。
阶段状态：PASS

