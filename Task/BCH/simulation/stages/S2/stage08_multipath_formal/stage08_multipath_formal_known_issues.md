# stage08_multipath_formal 已知问题

- 不同 Case 使用 formal 前人工冻结的不同 Eb/N0 网格，因此自身高端工作点
  BER/FER 不应描述为完全相同 SNR 下的绝对横向优势；结论已明确限定。
- checkpoint 每 1000 帧保存完整时延样本，文件可能随单点帧数增长；完成点后
  自动删除，checkpoint 中间文件不提交。
- 时延为 Windows/MinGW 软件 wall-clock 结果，受主机调度影响，不代表硬件。
- 误纠与未检测错误按“decoder reported success 且 payload 错误”统计，
  两列在当前硬判决 BCH 接口下数值相同，但均保留以满足状态审计。
- 未执行 AWGN 对比、CFO、多普勒、时变衰落或信道估计误差实验，这是明确非目标。

没有未解释的 stage08 阻塞项。
