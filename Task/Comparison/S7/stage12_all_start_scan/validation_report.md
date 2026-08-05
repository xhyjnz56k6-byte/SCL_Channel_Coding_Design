# Stage12 验证报告

- 自动工作点：BCH -5/5.5/10 dB；CC -5/-3/10 dB，PASS。
- framesPerStart：200；同组四配置共享 payload/noise/frameSequenceHash，PASS。
- BCH：1587 组、6348 行，5%=272 起点/工作点，10%=257 起点/工作点。
- CC：3402 组、13608 行，5%=582 起点/工作点，10%=552 起点/工作点。
- 起点集合严格等于 `0..N-L`：PASS。
- 两步 group-limit 恢复预检：2 组→4 组，16 行且无重复/半组，PASS。
- 正式 checkpoint：COMPLETE；stderr：0 bytes。
- 聚合：48 行，含 mean/worst/best/start/failureStartRatio/boundary/tail 指标。

Gate：PASS_STAGE12_ALL_START_SCAN。

## 2026-08-05 BCH 2%补扫

- 原因：Stage15 正式热力图改为 BCH 2% 与 5%，历史全起点数据只含 5%/10%。
- 范围：仅 BCH 2%；保持工作点 -5/5.5/10 dB、每起点 200 帧、四配置、共享 payload/noise/frameSequenceHash。
- 输出：`results/bch_2_percent/all_start_results.csv`，3360 行、840 组、每工作点 280 个完整起点。
- configHash：单一且与冻结 Stage12 runner 一致；NaN/Inf：0。
- Gate：PASS_STAGE12_BCH_2_PERCENT_SUPPLEMENT。
