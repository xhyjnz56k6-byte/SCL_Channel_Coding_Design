阶段名称：
stage21_formal_metadata_repair

实验目的：
Repair formal case metadata without rerunning Monte Carlo

主要输入：
K=300；N480/N560/N640；α=0.95/0.95/0.80；Es/N0=-5:0.5:10 dB；
minFrames=1000，targetFrameErrors=200，maxFrames=50000，maxIterations=32。

完成内容：
只记录本阶段真实执行的代码、检查、仿真和结果处理。

主要输出：
results/ 下的 CSV、JSON、PNG、日志和报告。

当前结论：
详见 validation_report.md 和 results/。

已知问题：
时延受操作系统调度影响；有限帧结果不用于武断判定 error floor。

阶段状态：
PASS
