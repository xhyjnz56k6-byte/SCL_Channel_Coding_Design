阶段名称：stage06_ldpc_result_integration

实验目的：整合 Direct BG2 N560 的 BP/NMS 历史正式结果。
主要输入：Stage23 修订 Formal 点表；K=300、N=560、Zc=56、maxIter=32、NMS alpha=0.95。
完成内容：已定位并整合 BP/NMS 各 31 点，通过成对 payload/codeword/LLR 哈希检查。
主要输出：ldpc_n560_integrated_results.csv、source inventory 和 Gate 摘要。
当前结论：62 行 N560 主结果 Gate 通过；无需重跑 LDPC Formal。
已知问题：10/20/30 次迭代没有正式性能对比；代码能力不等于正式结果存在。
阶段状态：PASS
