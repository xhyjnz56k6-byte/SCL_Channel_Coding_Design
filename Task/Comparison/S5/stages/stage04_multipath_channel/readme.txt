阶段名称：Stage04 固定多径信道

任务目的：实现固定三径多径信道及接收端已知信道条件下的均衡和软信息计算。
任务作用：在受控、可复现的码间干扰条件下比较卷积码与 LDPC 的性能，而不是声称覆盖任意真实传播环境。
完成内容：冻结单位能量实抽头 [1, 0.65, 0.35] 与延迟 [0, 1, 3]；接收端使用实轴线性 MMSE：A=(H^T H+sigmaSquared I)^(-1)H^T；使用逐符号 gk/vk 对角高斯近似生成 LLR。
结果：恒等与固定向量、gk/vk 有限正值及 MATLAB LLR 参考均通过，功能门禁为 PASS_S5_MULTIPATH。
如何使用本目录：frozen_config.csv 保存抽头和延迟；result_summary.csv 给出三项 PASS；validation_report.md 说明 MMSE 与 LLR 验证。
