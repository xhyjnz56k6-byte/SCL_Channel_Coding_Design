阶段名称：Stage12 短时遮挡下卷积码独立验证

任务目的：独立复核 Stage10 中卷积码 R1/2 与 R2/3 在 5% 已知短时遮挡下 FER 接近 1 的现象，重点验证 R2/3。
任务作用：判断该平台现象是否来自实现错误；它是 Stage10 正式结论的正确性审计，不是新增 Formal，也不替代 Stage10 的统计数据。
完成内容：进行参数审计、固定 trace、C++ 最小遮挡比例扫描、MATLAB 官方卷积码独立链路和 17×27 块交织诊断。固定向量共享原始 payload，但 C++ 与 MATLAB 独立编码、打孔和译码；独立统计使用不同 payload 与 AWGN 随机种子。
结果：C++ 在 4、8、10 dB 的 CC R2/3 FER 均为 0.998；MATLAB 对应 FER 为 0.999、0.999、1.000。17×27 交织诊断在这三个点的 5000 帧统计中 FER 为 0，仅用于解释机制，未写入 Stage10 方案比较或推荐。
结论与边界：门禁 PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION。验证支持 Stage10 的短时遮挡结论；MATLAB 不参与 LDPC 对比，交织不属于正式方案。
如何使用本目录：result_summary.csv 提供 C++/MATLAB 统计值；stage12_parameter_audit.md、validation_report.md 和 commands_used.md 提供审计证据。
