阶段名称：
stage02_bch_complexity_instrumentation

实验目的：
为 BCH-S200 syndrome lookup 与 BCH-B200 BM+Chien 增加算法事件、底层操作和存储量统计。

主要输入：
S200 200 bit/285 bit、B200 200 bit/248 bit，无噪声与确定性错误模式。

完成内容：
复杂度计数结构、存储核算、适配器导出与单元测试。

主要输出：
源码修改、test_bch_s6_metrics、validation_report.md。

当前结论：
Release 单线程构建成功，8 项 CTest 全部通过，BCH 复杂度与内存 Gate 通过。

已知问题：
STL 分配器元数据不计入 EXACT_FROM_TYPE_AND_COUNT；报告必须明确这一边界。

阶段状态：
PASS
