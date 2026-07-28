# stage07_multipath_validation 已知问题

- stage07 trial 每 Case 仅 3 个、每点 500 帧，只用于链路、schema、运行时间与
  stage08 人工网格冻结，不构成正式性能结论。
- 时延为当前 Windows/MinGW 软件实现的 wall-clock 观测，不代表硬件时延。
- stage08 尚未执行；其正式停止规则可能使零误帧点运行到 50000 帧。
- 未加入 CFO、多普勒、时变衰落或信道估计误差，这是本 Stage 明确非目标。

没有未解释的 stage07 阻塞项。
