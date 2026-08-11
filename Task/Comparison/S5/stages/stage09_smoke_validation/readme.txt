阶段名称：Stage09 Smoke 验证与 Formal 就绪检查

任务目的：在不改变已冻结编译码源代码的前提下，关闭 Formal 前的审计问题，验证程序、固定向量、恢复执行和网格 Smoke 是否可进入正式实验。
任务作用：这是 Stage10 Formal 的串行前置门禁；Smoke 未通过时不得执行正式 BER/FER 统计。
完成内容：完成 Release 编译和单元测试；检查 2160 条固定向量；进行 264 个唯一方案点、7,929,674 个 scheme-frame 的网格 Smoke；核验四个中断后恢复任务与连续运行完全一致；补充 5% 短时遮挡网格。
结果：22/22 就绪检查通过，功能门禁为 PASS_S5_FORMAL_READINESS，并获得 PASS_S5_SMOKE。5% 短时遮挡成为 Formal 主场景，10% 遮挡仅保留为压力测试。
已知限制：两条卷积码短时遮挡曲线在 5% 遮挡下仍接近 FER 0.998 至 1.0；该现象随后由 Stage12 独立验证，未进行第三次调参。
如何使用本目录：result_summary.csv 汇总所有 Gate；formula_audit.md 记录公式审计；commands_used.md 记录复现命令。
