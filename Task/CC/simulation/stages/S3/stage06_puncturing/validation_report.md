# Stage06 验证报告

Gate：`PASS_STAGE06_CC_PUNCTURING`

- 分支：`stage01-cc`
- baseCommit：`380cebe679bc30a977c0f51e5cc5ce06bed1fce1`
- contentCommit：`074474416a92bebcc63c6deb6bed3474d2f2fd46`
- mergeStatus：`NOT_MERGED`

实际结果：

- Release build 与 CTest：1/1 PASS；
- 四候选无噪声：各 120 帧，hard/soft 全部恢复；
- 分段打孔相位携带：PASS；
- R23 长度 459、actualRate 0.6535947712418301；
- R34 长度 408、actualRate 0.7352941176470589；
- MATLAB 四图样打孔、hard、soft mismatch：0；
- Stage03/04 回归：PASS；
- `git diff --check`：PASS。

首次 CTest 因未传 results 参数失败，修复 CMake 注册后重跑通过。小 AWGN 选择冻结 R23=`1101`、R34=`110110`，不作为 formal 结论。

首次审计提交后，`git diff --check` 对作为新增文本文件的 `changes.patch` 中标准 unified context 空行报 trailing whitespace。功能范围自身的 `git diff --check base..content` 为 PASS。审计修复将 patch 重新由同一真实 Git diff 以 `--unified=0` 生成，避免上下文空行歧义；随后工作区和 staged diff 检查均通过。

远程分支 `origin/stage01-cc` 已验证包含本 Stage 功能提交；未合并 `main`。
