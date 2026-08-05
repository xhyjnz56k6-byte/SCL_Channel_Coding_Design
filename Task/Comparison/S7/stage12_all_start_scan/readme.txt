阶段名称：stage12_all_start_scan
实验目的：在自动选择的低、waterfall、高工作点，对 5% 和 10% 连续极性反转遍历全部合法起点。
主要输入：Stage10/11 Formal CSV、BCH/CC 四配置、每起点 200 个共享帧。
完成内容：BCH 1587 组/6348 行、CC 3402 组/13608 行全部完成；恢复预检、全起点 checker 和聚合分析通过。
主要输出：逐起点 CSV、48 行汇总 CSV、checkpoint、验证报告。
当前结论：BCH 工作点为 -5/5.5/10 dB，CC 为 -5/-3/10 dB；CC 高工作点 10% 突发所有配置最坏起点 FER 均为 1。
已知问题：逐起点 FER 分辨率为 0.005；CC waterfall 由 BER 下降主导，FER 仍饱和。
阶段状态：PASS
