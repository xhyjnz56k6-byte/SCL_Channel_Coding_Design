阶段名称：Stage03 AWGN 回归验证

任务目的：在最基本的 AWGN 信道下，确认四种比较方案的编译码链路和实轴 LLR 完整正确。
任务作用：AWGN 是其余五类受控信道的基线；后续的性能损失均相对于同一方案自己的 AWGN 结果计算。
完成内容：完成四方案无噪声回归、C++ 固定向量检查，并用 MATLAB 官方 poly2trellis、convenc、vitdec 独立核验卷积码编译码和穿孔位序。
结果：四方案无噪声、C++ 固定向量和 MATLAB 官方卷积码参考均通过，功能门禁为 PASS_S5_AWGN。
如何使用本目录：result_summary.csv 给出三项 PASS；frozen_config.csv 记录 AWGN 参数；validation_report.md 给出详细验证证据。
