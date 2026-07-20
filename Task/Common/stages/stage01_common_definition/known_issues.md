# Known Issues

No known blocking issues.

## 未执行项

- Common-02 类型和接口骨架未执行。
- Common-03 公共帧池未执行。
- Common-04 随机种子和每帧独立噪声生成器未执行。
- Common-05 BPSK、AWGN、硬判决和 LLR 实现未执行。
- Common-06 指标、置信区间、时延和停止控制实现未执行。
- Common-07 checkpoint/resume、trace、结果输出和图片实现未执行。

## 当前限制

- 本阶段只冻结定义，不生成实际帧池、噪声文件、仿真结果或图片。
- 本阶段已推送 `main` 和 `stage01-common-definition` 到 origin；最终是否修改 GitHub 默认分支仍需在 GitHub 页面确认。

## 仍存在的歧义

- No known definition ambiguity remains for Common-01.
- GitHub 默认分支可能仍显示为 `stage01-common-definition`，但远程 `main` ref 已存在，可执行 `main...stage01-common-definition` 比较。

## 后续 Common-02 才处理的事项

- C++ 类型、接口、目录骨架和编译测试。
