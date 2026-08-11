阶段名称：Stage10 正式多信道仿真

任务目的：执行并审计已冻结的 S5 正式实验，生成可用于最终报告的 BER、FER、译码迭代和软件时延数据。
任务作用：这是 S5 唯一的正式统计数据来源；Stage11 图表、推荐表和 Aggregate 图均只能读取这里的合并 CSV。
完成内容：比较 AWGN、固定多径、30 度固定频偏、多普勒频移、5% 短时遮挡和 5% 未知突发干扰；使用 31 个 Es/N0 点（-5 至 10 dB，步长 0.5 dB）；执行 372 个配对任务、744 个唯一方案点、8,115,263 个配对帧和 16,230,526 次方案译码。
结果：行数、停止条件、有限数值、配对帧数、策略与哈希均通过，功能门禁为 PASS_S5_FORMAL。正式合并数据为 results/formal/merged/formal_merged_results.csv。
已知限制：时延是本机 Windows Release 软件测量，不是硬件时延保证；六类信道均为受控比较模型，不外推为通用工程或真实卫星链路结论。
如何使用本目录：commands_used.md 和 frozen_config.csv 用于复现；validation_report.md 说明 Gate；结果文件应从 results/formal/merged/ 读取。
