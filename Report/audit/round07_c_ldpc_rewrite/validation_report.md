# Round07-C 验证报告

## 验证结论

Round07-C 功能 Gate 为 **PASS（仅工作区）**。第 6 章已完成报告化重构，附录参数表同步修订；既有正式结果、LDPC 代码和算法配置保持不变。用户要求本轮不执行 Git 发布，因此功能范围尚无提交区间。

## 实际执行的检查

| 检查项 | 实际结果 | Gate |
|---|---|---|
| 分支检查 | 当前分支 `S8-PaperDocu`，不是 `main` | PASS |
| 第 6 章结构扫描 | 10 节、10 个 Figure 环境、11 个 Table 环境、5 个 Equation 环境 | PASS |
| 图形构成 | 3 个 Visio 占位图、7 组正式结果图、13 个 PNG 引用 | PASS |
| 正文字数 | 4069 个汉字字符 | PASS |
| 禁用元话语扫描 | 指定 Stage/Git/审计/待定类词项命中 0 | PASS |
| XeLaTeX 编译 | 成功生成 `Report/main.pdf`，109 页 | PASS |
| LaTeX 日志 | Overfull、未定义引用/引文、Fatal error、Label changed 均为 0 | PASS |
| 第 6 章视觉检查 | 打印页 74--90 共 17 页逐页渲染检查，无裁切、重叠、异常空页或顺序错误 | PASS |
| 附录视觉检查 | A.5 打印页 99 渲染检查，参数表与说明完整 | PASS |
| 正式输入 CSV 完整性 | `input_hashes.csv` 所列 7 个 CSV 的 SHA-256 全部一致 | PASS |
| 正文 PNG 完整性 | 13 个报告 PNG 与正式源图逐一同哈希 | PASS |
| LDPC 功能目录保护 | `git diff -- Task/LDPC` 无差异 | PASS |
| Git 空白错误检查 | `git diff --check` 无错误；仅显示仓库既有换行风格提示 | PASS |
| 非授权操作检查 | 未提交、未推送、未合并、未切换分支、未重跑正式仿真 | PASS |

## 定量复核

- FER 工作点采用相邻非零样本的 `log10(FER)` 线性插值，无外推；派生值保存在 `derived_fer_workpoints.csv`。
- NMS 归一化因子统计来自既有扫描结果；关键均值和 0.90/0.95 差异保存在 `alpha_key_results.csv`。
- 第 6 章采用实际发送码长 480、560 和 640 bit；未把目标 576 bit 写成实际码长。
- 最大时延仅作为相邻正式样本中的保守观测列入表格，并明确区分平均值、P95 与受操作系统调度影响的最大观测值。

## 工作区边界

本轮功能文件仅为第 6 章正文和附录 A；审计目录记录计算、哈希与视觉检查。工作期间出现的 `Task/Comparison/S5` 改动不属于 Round07-C，未被本轮修改或纳入 Gate。
