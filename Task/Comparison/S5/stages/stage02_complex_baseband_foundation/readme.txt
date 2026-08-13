阶段名称：Stage02 复基带基础

任务目的：为 S5 建立统一的 BPSK 复基带发送、Es/N0 噪声和软信息接口。
任务作用：使后续多径、频偏、多普勒频移和突发干扰能够在同一复信号模型上比较，同时保持 Common-04 的既有噪声策略不变。
完成内容：实现 BPSK 复表示；引入 s5_complex_pair_v1 在线独立 I/Q 高斯噪声；实现有限的无噪声软度量，避免出现 2y/0；不生成完整 50000 帧复噪声池。
结果：在线复噪声、I/Q 独立性和长度 1280 检查均通过，功能门禁为 PASS_S5_COMPLEX。该阶段输出的是基础正确性结果，不是正式 BER/FER 比较。
如何使用本目录：frozen_config.csv 保存冻结参数；result_summary.csv 给出三项 PASS；commands_used.md 和 validation_report.md 保留复现记录。
