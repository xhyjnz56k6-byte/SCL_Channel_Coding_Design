# Known issues

- Stage07/08 横轴需从 waveform-SNR 转为报告 Es/N0；原数据不可覆盖。
- Stage17 最终全信道 Gate 尚未生成，原因是合并内容 whitespace check，不是数值失败。
- 旧固定初相位专题缺少当前同级源码追溯，分类为 VALIDATION/SUPERSEDED。
- W9 与早期 BCH16 审计文件存在历史状态文字差异；本轮未修改历史审计文件。
- 未重跑 formal、MATLAB 或编译测试；本轮结论来自当前源码、既有正式 Gate 和只读数值复算。
