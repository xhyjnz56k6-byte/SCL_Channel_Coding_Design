阶段名称：Stage08 突发干扰信道

任务目的：实现 5% 单段连续复高斯突发干扰，并规定接收端未知干扰位置的处理方式。
任务作用：与短时遮挡形成对照：短时遮挡的 mask 已知且 LLR 为零；本阶段的突发干扰 mask 未知，接收端仍使用名义 AWGN LLR。
完成内容：冻结 burstFraction=0.05、ISR=10 dB，干扰缩放 beta=sqrt(10^(ISR_dB/10)/2)=sqrt(5)；向连续区间叠加复干扰；禁止将其误实现为擦除、比特翻转或交织场景。
结果：突发区长度和起点不回绕、beta=sqrt(5)、名义 LLR 且不置零均通过，功能门禁为 PASS_S5_BURST。
如何使用本目录：frozen_config.csv 保存 ISR 和接收机假设；result_summary.csv 给出三项 PASS；known_issues.md 记录未实现干扰检测与消除。
