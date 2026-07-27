# stage05_awgn_trial 验证报告

最终 Gate：`PASS_STAGE05_AWGN_TRIAL`

- Release 构建与 CTest：1/1 PASS；
- 固定试运行：8 Case × 3 点 × 500 帧，共 24 点；
- AWGN、实际码率、sigma²、SNR、BER/FER 原始计数复算：24/24 PASS；
- checkpoint/resume：8/8 原始整数计数与母噪声 checksum 完全一致；
- 三分片合并：8/8 原始整数计数与母噪声 checksum 完全一致；
- stage06 停止规则边界测试：4/4 PASS；
- 试运行图：K=200/K=300 的 BER/FER 共 4 张 300 dpi PNG；
- 每张图均有独立 figure-data CSV，聚合数据与 plot manifest 已保留；
- 中文字体显式冻结为 Microsoft YaHei，最终绘图日志无缺字警告；
- 人工目视抽查 `stage05_awgn_trial_k200_ber.png` 通过。

第一次完整运行因 checker 将聚合图数据的正确 48 行误期望为 96 行而阻断；第二次虽通过
业务 Gate，但发现中文字体警告；修正后第三次完整流水线无警告通过。只有第三次结果用于
本报告和功能提交。

- functional base：`264a6ac2827eb65f187ef7335c9af777a5af5d14`
- functional content：`a5310744515a24d9e8d4736e5c71289c0df0b283`
- 修改范围仅为 stage05；
- 本地 `results/` 明细未进入功能提交；
- 当前 AWGN 分支没有被 push，`main` 没有合并。
