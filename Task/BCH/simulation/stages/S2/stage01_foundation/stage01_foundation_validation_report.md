# stage01_foundation 验证报告

## 结果

最终 Gate：`PASS_STAGE01_FOUNDATION`

## 实际执行

- Release 配置和 MinGW GCC 15.2.0 构建：PASS。
- CTest：1/1 PASS，日志非空。
- C++ 固定 AWGN 数值导出：20 行。
- MATLAB R2024b 独立数值参考：PASS。
- C++/MATLAB 连续量比较：20/20 PASS，容差 `1e-12`。
- 硬判决离散 mismatch：0。
- 随机身份测试：6/6 PASS。
- 公式复算：20/20 PASS。
- 结果和日志 SHA-256：PASS。

随机性测试确认同一完整身份完全复现；改变 `stageId`、`caseId`、
`ebn0Index`、`frameIndex` 或 `randomDomain` 会改变随机序列；checkpoint/resume
和 shard 对同一逻辑帧不改变噪声。

## 失败与修复记录

前两次 MATLAB 执行因 `table` 的变量名参数形式不兼容而失败。没有继续 stage02。
改用字符向量元胞数组后，从构建、CTest、导出、MATLAB 到比较完整重跑，第三次通过。

## 复用说明

审查了 `Task/Common` 的 BPSK、AWGN、随机策略、checkpoint 和 metrics 定义，以及
旧 BCH AWGN Stage。未修改 `Task/Common`，也未复制旧 CSV 或 PNG。新代码采用本任务
冻结的 `10*log10(2*R)` SNR 换算，并新增完整随机身份字段。

## Git 与范围

- functional base：`069373b02401ad0acc10d96eb4e63bad8763c64c`
- functional content：`3c41bc7194ff16547f8d6f12d5e21c2d1e2074f9`
- 修改范围仅为 `Task/BCH/simulation/stages/S2/stage01_foundation`
- push 未获授权，因此未执行。
- `main` 未合并。
