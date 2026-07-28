# Stage09 验证报告

Gate：`PASS_STAGE09_CC_AWGN_FORMAL`

- 分支：`stage01-cc`
- baseCommit：`311e51d6eab305fc65bf31b0ed315fd07c0b72e9`
- contentCommit：`84c6a54a7b29d629223b796d1edea857fc6f8460`
- mergeStatus：`NOT_MERGED`

已实际执行 Release 编译、100 帧处中断/恢复与 400 帧连续运行对照、错误 checkpoint 配置拒绝、两个正式 shard、merge 正负向 mutation、逐点公式检查、五图生成与哈希检查、图像目视 QA、Stage08 审计回归和 `git diff --check`。

正式结果包含 6 个 Case、126 个 SNR 点和 825696 帧。所有点的 frameIndex 均为 `[0, framesProcessed)`，frameSequenceDigest、BER/FER、actualRate、Eb/N0、sigmaSquared、goodput 和停止条件均通过；重复点、缺失点、跳帧和覆盖旧正式输出的 mutation 均被拒绝。五张科研图文字、图例、坐标和曲线可读，无裁切。

FER=0.1 只在 hard/soft 两条曲线都覆盖目标时进行对数 FER 线性插值，得到 hard 相对 soft 增益：1/2 为 2.085 dB、2/3 为 1.927 dB、3/4 为 1.857 dB；未使用外推。

首次按统一 0.2 dB 生成工作单元时，R23/R34 因冻结端点不在同一网格而被 merge Gate 拒绝，未写正式输出。随后将这两个码率改用任务允许的 0.1 dB，保留失败 runtime 并在新 `formal_v2` 目录完整重跑。

远程验证延后至 Stage15 后统一 push；未合并 `main`。
