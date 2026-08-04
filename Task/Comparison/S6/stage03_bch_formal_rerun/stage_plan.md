# Stage03 BCH 正式重跑计划

## 目标

按冻结 Es/N0 网格完成 S200/B200 正式重跑，并保留逐点停止原因、译码时间、复杂度、内存、环境和哈希。

## 非目标

不改变 BCH 码型；不运行 300 bit BCH；不修改历史 CSV；不提交或推送。

## Gate

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| Es/N0 公式 | BCH AWGN runner | 单点公式检查 | 不一致抛异常 | 误差 <= 1e-12 |
| 正式停止条件 | run_bch_formal.ps1 | 62 点汇总检查 | 缺点/越界失败 | 31×2 点完整 |
| 复杂度统计 | complexity_summary.csv | total/avg/P95/max | 缺字段失败 | 字段完整且非负 |
| 环境记录 | execution_environment.* | JSON 可解析 | 缺字段失败 | 必需字段齐全 |
