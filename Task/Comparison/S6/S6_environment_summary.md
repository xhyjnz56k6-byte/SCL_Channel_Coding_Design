# S6 执行环境摘要

- CPU：Intel(R) Core(TM) i5-14400F（10 物理核 / 16 逻辑处理器）
- 内存：34055565312 byte
- 操作系统：Microsoft Windows 11 家庭版 中文版，版本 10.0.26200，Build 26200
- 编译器：g++.exe (Rev8, Built by MSYS2 project) 15.2.0
- 标准与构建：C++17，Release，-O3 -DNDEBUG (CMake MinGW Release default)
- 线程：1；计时钟：std::chrono::steady_clock
- 计时范围：hard decision ready -> decodeBchFrame -> payload and status ready
- 预热：100 帧；逐帧日志：False
- 动态分配是否包含在计时中：True
- 电源方案：电源方案 GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (平衡)
- 可执行文件 SHA256：`b4d1a36bc6953d030b08862b7f333c722a4551e3895178752e7ac5c93c42ca30`
- Git：`S6-Comparision` / `9d51fabdaa8446966f70c395d552576b3ab7fb52`；正式运行时工作区状态已完整保存在环境 JSON。

时延仅适用于当前 CPU、操作系统、编译器、Release 配置和线程环境；最大时延是平台相关观测值，不是理论最坏上界。
