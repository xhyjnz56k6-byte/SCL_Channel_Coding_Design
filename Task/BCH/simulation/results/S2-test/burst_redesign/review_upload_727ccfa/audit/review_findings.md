# S2-07 自动化与审计复核发现

复核基线：`5ecf3d57a577abeb1d0f89f6a7b31cdd6d83c26e`

以下问题均在修改前通过源码或现有产物确认：

1. `--resume` 仅由 argparse 解析，未参与运行逻辑。
2. `bch_burst_runner` 使用 `std::ofstream(output)` 截断结果，不支持恢复。
3. `check_bch_s2_burst_resume_shard.py` 使用固定的假 shard 计数。
4. resume 与 uninterrupted 的成功状态由固定字符串声明。
5. 统一驱动直接写入内容为 PASS 的 `resume_shard_audit.csv`。
6. `--matlab-only` 只打印说明，没有启动 MATLAB。
7. `--all` 没有执行 burst redesign MATLAB reference。
8. 最终 checker 没有读取并验证 MATLAB mismatch summary。
9. 最终 checker 没有实际执行 CTest、保存返回码和完整日志。
10. 绘图 checker 没有完整验证 style tuple、legend 和 source/figure-data
    逐点对应关系。
11. `uniformBurstStart` 使用 `% legalCount`，存在 modulo bias。
12. S200/S300 全范围热力图过度饱和，缺少局部边界、理论保证区和
    `L=2` 直观解释；S2-07D 也缺少超纠错能力帧占比图。

在本轮真实验证全部完成前，历史
`PASS_BCH_S2_BURST_REDESIGN_AND_PLOT_QUALITY` 不作为有效最终 Gate。

## 修复状态

上述 12 项均已完成代码修复和本地功能验证：

- checkpoint/resume：真实中断于第 113 帧后恢复，与连续 300 帧的 13 个
  原始计数字段及 frame index 序列完全一致；
- shard：真实执行 3 个互斥 shard 并合并，duplicate、missing、seed、
  config、case、length、interleaver、overlap 均被拒绝；
- MATLAB：实际启动 MATLAB，完成 15 组、9040 帧比较，8 类 mismatch
  均为 0；
- CTest：checker 现场执行 4 项测试并保存完整日志与 SHA-256；
- 绘图：18 张图逐图核验源数据、figure-data、哈希、点数、有限值、
  legend、style tuple、零值策略及 nearest 插值；
- 随机起点：改为确定性 rejection sampling，并通过覆盖与卡方
  sanity test。

普通 push 和远程包含性验证完成前，批次总 Gate 保持
`FUNCTIONAL_PASS_REMOTE_PENDING`。
