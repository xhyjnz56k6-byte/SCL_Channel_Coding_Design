# stage06_awgn_formal 验证报告

最终 Gate：`PASS_STAGE06_AWGN_FORMAL`

总 Gate：`PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06`

- Release 构建与 CTest：1/1 PASS；
- 8 Case × 5 点：40/40 PASS；
- 正式总帧数：755381；
- `TARGET_FRAME_ERRORS_REACHED`：30 点；
- `MAX_FRAMES_REACHED`：10 点；
- 原始计数、BER/FER、实际码率、sigma² 与 SNR 复算：40/40 PASS；
- checkpoint：40/40；单分片 manifest 与 identity merge audit：40/40；
- 正式图：K=200/K=300 的 BER、FER、译码平均时延共 6 张 300 dpi PNG；
- 每张图有独立 figure-data CSV，另有聚合数据与哈希 manifest；
- 人工目视抽查 K=300 时延图通过，中文、图例、单位与 SNR 轴正常；
- 第一次运行由 24 点读取契约阻断，第二次由时延聚合缺失阻断；修复后第三次从头完整通过。

正式结果的 `gitCommit` 字段记录运行启动时已审计 HEAD
`7c1f21fdbcca40e4248f7fd21c241078cd964357`；本 Stage 全部实现、日志与发布图由
functional content `0e622e850e545891253cc9b134f7a36a97f72dd2` 固化。

当前 AWGN 分支未 push，`main` 未合并，多径实验未启动。
