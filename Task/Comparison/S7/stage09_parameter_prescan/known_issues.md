# Stage09 已知问题

- 每 case 50 帧，仅用于筛选，FER 数值不可作为正式科研结论。
- 37/72 组有区分度，其余饱和组完整保留但不驱动归一化排名。
- CPU 时间受 Windows/MinGW 与系统负载影响；Stage10 前应以 Release runner 校准。
- checkpoint 恢复字段已冻结，但真实终止/恢复一致性尚未在 Formal runner 上执行。
- 擦除和强干扰扩展未做。
- Formal、科研图和最终结论均未启动。

