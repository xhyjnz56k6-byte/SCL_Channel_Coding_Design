# Stage02 验证报告

- GNU C++ 15.2.0、C++17、Release、单线程构建：PASS
- CTest：8/8 PASS
- BCH(15,11,1) 2048 个消息无噪声：PASS
- S200 19 个分段单错恢复与计数：PASS
- B200 0～6 错恢复、BM/Chien 与译后综合征：PASS
- 计数非负、内存字段有效：PASS

Gate：`PASS_BCH_COUNTER_UNIT_TESTS`、`PASS_BCH_MEMORY_ACCOUNTING`
