# Stage10 验证报告

Gate：`PASS_STAGE10_CC_TRACEBACK_STUDY`

- 分支：`stage01-cc`
- baseCommit：`4feb90e38a6540d7901e24c6d6d754bb29eb9313`
- contentCommit：`17d65c1c433943af2c80415e1bccf76e9c3e5bd4`
- mergeStatus：`NOT_MERGED`

已实际执行 Release 编译、四个无噪声有限回溯检查、4 场景×1000 帧×4 模式实验、逐行公式/有限值/内存/操作数/mismatch 检查、推荐门限 checker、Stage09 审计回归和 `git diff --check`。

严格 5% BER/FER 优先门限没有候选通过，checker 首次因此停止。数据复核显示 Dtb70 的最坏 BER 增幅 5.696%、最坏 FER 增幅 12.987%，同时 survivor 内存减少 77.124%；Dtb35/49 损失更大。因此按明确记录的 fallback 门限冻结 Dtb70，推荐等级为 `FALLBACK`，不得称为无损等价。

当前有限回溯研究实现因对每个输出重复 traceback，平均时延不优于完整块；Stage12 需要用窗口调度重新测量。远程分支 `origin/stage01-cc` 已验证包含本 Stage 功能提交；未合并 `main`。
