# stage08_multipath_formal 验证报告

最终 Gate：`PASS_STAGE08_MULTIPATH_FORMAL`

## 正式配置与运行

- 8 Case、24 个 formal 前冻结 Eb/N0 点。
- `minFrames=5000`、`targetFrameErrors=200`、`maxFrames=50000`。
- 正式源提交：`5fb6a373263eb6a50d0ef70a14cad16963a0fb3d`。
- config hash：`457ea7422976679d98dd9ca6857c00c84e2fbb71e546f759d4ff745aac299a84`。
- 2 个互斥 shard，总计 `391572` 帧。
- 18 点因达到 200 错误帧停止；6 点运行至 50000 帧。
- 每帧 payload/AWGN 与完整逻辑身份绑定，不依赖执行顺序。

## 实际 Gate

- runner frozen grid/self-test：PASS。
- 2500 帧强制中断、1000 帧间隔 checkpoint、恢复与连续运行：
  8 项整数计数完全一致。
- 完成点 resume：24/24 跳过，shard CSV SHA-256 不变。
- shard merge：24 个唯一点，无重复 Case/Eb/N0；git/config 一致。
- rate、sigma2、snrLinear、snrDb、BER、FER 与整数计数复算：24/24 PASS。
- `trueSuccessFrames + payloadErrorFrames = totalFrames`：24/24 PASS。
- stopReason 和帧数：24/24 PASS。
- NaN/Inf：0；最大 solver residual `2.68901431863089e-16`，
  小于 `1e-11`。
- 8 个 PNG、8 个 figure-data、8 个逐图 manifest、8 个逐图 checker log：
  PASS。
- 禁止格式 PDF/SVG/EPS/JPG/JPEG：0。
- 原始零 BER/FER 未修改；log 图 surrogate 仅用于显示并在 figure-data 标记。
- `PASS_STAGE08_PLOT_CHECK`。

## 正式结果与结论

- 200 bit：可靠性高端工作点与最低译码时延为 `K200_S15`；最高码率和
  最低 MMSE 时延为 `K200_M255K207`；综合折中推荐后者。
- 300 bit：自身高端最低 BER 为 `K300_S15`，最低 FER、最高码率和综合折中
  为 `K300_M511K421`；最低译码时延为 `K300_S15`。
- 结论限定于冻结工作点，不声称存在脱离 SNR/网格的单一绝对最优。

## Git 与范围

- branch：`stage07-08-bch-s2-multipath`
- implementation：`7d634814ee50c246a84557d137ceb2c0d7120596...e055724b05f86f42c3ffe3e602f842303426f405`
- checkpoint/checker repair：`e055724b05f86f42c3ffe3e602f842303426f405...5fb6a373263eb6a50d0ef70a14cad16963a0fb3d`
- formal data：`5fb6a373263eb6a50d0ef70a14cad16963a0fb3d...77910900d1db3eb64142f409b3b68e4ca9db010f`
- 远程分支已推送上述提交。
- `main` 未合并。
