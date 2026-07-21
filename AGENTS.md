# SCL_Channel_Coding_Design 项目规则

## 1. 项目范围

本工程包含三类信道编码：

- `Task/BCH`：BCH 编码、译码与仿真；
- `Task/CC`：卷积编码、Viterbi 译码与仿真；
- `Task/LDPC`：BG2 Direct QC-LDPC、Layered BP 译码与仿真；
- `Task/Common`：公共帧池、标准高斯母噪声、随机种子和公共格式。

核心编译码算法使用基础、清晰的 C++ 实现。Python 只负责驱动编译、测试、数据生成、结果检查和绘图；MATLAB 用于独立参考验证。

## 2. 目录规则

- BCH 专用代码、脚本、`build` 和 `results` 必须位于 `Task/BCH`。
- 卷积码专用内容必须位于 `Task/CC`。
- LDPC 专用内容必须位于 `Task/LDPC`。
- `Task/Common` 只能存放三类码真正共用的资源。
- 整块编码与分块编码必须使用独立目录。
- 每次任务使用唯一的 `stageXX_name`。
- 禁止覆盖或删除旧 Stage、旧代码和旧实验结果。
- 未经授权，禁止修改当前 Stage 范围外的编码目录。

## 3. C++ 要求

- 使用普通函数、简单 `struct`、循环、`std::vector`、`std::array`、文件流、随机数和 `chrono`。
- 禁止不必要的复杂继承、模板元编程、复杂 lambda、线程池和重型第三方库。
- 代码简单不能以降低算法正确性、译码性能或运行效率为代价。
- 编码、信道、解调、译码和统计模块应按流程拆分并独立测试。
- 正式仿真应预分配和复用内存，避免在核心循环中频繁分配内存、打印或写文件。

## 4. Git 规则

- `main` 只保存已经验证并审查通过的稳定代码。
- 禁止直接在 `main` 上修改、提交或推送。
- 默认每个 Stage 从最新且干净的 `main` 创建独立分支。
- 经用户明确授权，可以使用批次分支承载多个强相关 Stage。
- 使用批次分支时，每个 Stage 必须记录独立 functional range；单个 Stage checker 不得用整个 `main...HEAD` 作为自身功能边界。
- 分支名称使用 `stageXX-short-description`；批次分支可使用 `stageXX-YY-short-description`。
- Codex 只有在用户要求时，才可 commit 和 push 当前 Stage 或批次分支。
- Codex 禁止自动合并到 `main`。
- 是否合并由用户在代码和 GitHub 差异审查后决定。
- Codex 创建 commit 时，commit message 必须使用中文，格式为：
  `模块/阶段：简短说明`

## 5. 修改前检查

开始修改前，必须报告：

1. 仓库根目录；
2. 当前分支；
3. `git status`；
4. 当前 Stage 和目标；
5. 允许及禁止修改的范围；
6. 计划运行的测试；
7. 是否需要 commit 和 push。

如果当前分支是 `main`，必须停止修改并提醒用户创建 Stage 分支。

## 6. Stage 执行分层

默认按三个阶段执行；除非用户明确要求跳过，不得混在一起。

### 阶段 A：规格冻结

只读取和分析，不修改代码。必须输出目标、非目标、允许范围、禁止范围、接口或数据格式、验收矩阵和 Gate 条件，并等待用户确认。

验收矩阵格式：

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|

### 阶段 B：功能实现

只修改 Stage 范围内的源码、测试、业务 checker 和必要配置。执行编译、测试和业务 checker 后报告功能 Gate。默认不生成最终审计提交，不 push。

### 阶段 C：审计收口

功能冻结后，创建功能提交，生成或刷新 `manifest.json`、`validation_report.md`、`known_issues.md` 及 Stage 计划要求的其他审计文件，运行审计检查，按用户要求 push 并做远程验证。审计收口阶段默认不得继续扩大功能范围；如发现功能问题，必须回到功能实现阶段。

禁止自动合并 `main`，禁止自动开始下一 Stage。

## 7. 测试要求

- 每个模块必须有独立测试。
- 编码器和译码器必须先通过无噪声测试。
- BCH 和卷积码必须与 MATLAB 官方函数对比。
- Direct LDPC 必须与相同 BG2 子矩阵的 MATLAB 独立参考实现对比。
- smoke 未通过，禁止进入 prescan。
- prescan 未通过，禁止进入 formal。
- 未实际执行的测试不得标记为 PASS。
- 出现 mismatch、NaN、Inf 或校验失败时，必须停止并记录原因。

## 8. Stage 记录分级

每个 Stage 至少保留：

```text
stage_plan.md
manifest.json
validation_report.md
known_issues.md
```

- `stage_plan.md`：规格冻结阶段生成，记录目标、非目标、范围、接口/数据格式、验收矩阵和 Gate。
- `manifest.json`：机器可读审计清单，记录 Stage、分支、functional range、功能文件、Gate 和远程验证状态。
- `validation_report.md`：记录实际执行的编译、测试、checker、MATLAB/reference 对比和 Gate 结果。
- `known_issues.md`：如实记录未完成项、已知限制和未进入的后续 Stage。

按需保留：

- `changed_files.md`：可选，只写人工解释，不重复 `manifest.json` 的完整清单。
- `commands_used.md`：正式仿真、MATLAB 对比、formal、checkpoint/resume 或结果复现实验必须保留；轻量 Stage 可不强制。
- `frozen_config.csv`：配置冻结、仿真参数、随机种子或数据格式 Stage 必须保留。
- `result_summary.csv`：正式仿真或曲线结果 Stage 必须保留。

默认不强制提交：

```text
snapshot/
changes.patch
git_commit.txt
```

除非老师、用户或 Stage 计划明确要求。Git commit 本身作为源码快照和 patch 记录。

## 9. 审计强度分级

- 轻量 Stage：类型定义、接口骨架、小型工具、文档冻结。至少要求 build、unit test、业务 checker、`manifest.json`、`validation_report.md`、`known_issues.md`。
- 中等 Stage：公共帧池、随机种子、噪声源、信道基础、结果格式。至少要求正向测试、必要负向测试、一致性检查、manifest、validation report、known issues，必要时提交 `frozen_config.csv` 或 fixture 摘要。
- 重型 Stage：BCH/CC/LDPC 编译码、MATLAB/reference 对比、smoke/prescan/formal 仿真、checkpoint/resume、曲线和结果发布。必须保留 `commands_used.md`、`frozen_config.csv`、结果摘要、Gate 记录和 reference/MATLAB 对比记录。

## 10. Stage 审计收口规则

每个 Stage 必须区分规格冻结、功能实现和审计收口。

### 10.1 functional range

每个 Stage 必须在 `manifest.json` 中记录自己的 functional range：

```json
{
  "stage": "common03_frame_pool",
  "functionalRanges": [
    {
      "name": "content",
      "baseCommit": "...",
      "contentCommit": "...",
      "files": ["Task/Common/..."]
    }
  ]
}
```

如果同一 Stage 后续有功能修复提交，不得重写历史；应新增 functional range，例如 `originalContent`、`repairContent`。

### 10.2 批次分支审计

批次分支中，Stage checker 只检查 `manifest.json` 记录的 functional range。`main...HEAD` 只能用于批次总览和禁止目录检查，不能作为单个 Stage 的功能边界。

### 10.3 审计文件要求

- `manifest.json` 必须与真实 Git diff 一致：`git diff --name-status <baseCommit>...<contentCommit>`。
- `validation_report.md` 不得残留 `Pending`、`to be run`、`NOT_PUSHED`、`TO_VERIFY_AFTER_PUSH`。
- 已推送的功能提交不得记录为 `NOT_PUSHED`。
- 审计文件只记录被审计的功能提交 SHA，不记录审计提交自身 SHA，避免无限自引用。
- 审计文件与真实 Git 状态不一致时，Gate 不得标记为最终 PASS。

### 10.4 snapshot 和 changes.patch

默认不强制提交 `snapshot/` 和 `changes.patch`。如老师、用户或 Stage 计划明确要求提交，则必须说明语义，并由 checker 验证它们与 functional range 一致；`changes.patch` 必须由真实 Git diff 生成，不得包含自身递归，不得伪造连续历史。

## 11. 完成后报告

任务完成后必须报告：

1. 当前分支；
2. 新增、修改和删除的文件；
3. 实际执行的测试；
4. Gate 结果；
5. 已知问题；
6. commit hash；
7. 是否已 push；
8. GitHub 应比较的分支；
9. 明确说明未合并 `main`。

## 12. 禁止操作

未经用户明确授权，禁止执行：

```text
git reset --hard
git clean -fd
git clean -fdx
git push --force
git push --force-with-lease
git rebase main
git commit --amend
```

同时禁止：

- 自动合并 `main`；
- 重写 Git 历史；
- 删除旧 Stage；
- 覆盖旧结果；
- 删除失败测试来制造 PASS；
- 将 `.exe`、`.obj`、`.pdb` 等编译产物提交 Git；
- 自动进入下一 Stage。

## 13. 冲突处理

如用户指令、`AGENTS.md`、当前 Stage 计划、分支名称、现有实现或老师任务要求之间存在冲突：

1. 不得自行选择解释；
2. 不得通过扩大任务范围解决；
3. 必须停止修改；
4. 列出冲突项及其影响；
5. 等待用户确认后继续。

## 14. 生成内容和实验资产

以下目录和文件默认不提交 Git：

- `build/`
- `results/`
- 大型公共帧池；
- 公共噪声文件；
- MATLAB 临时文件；
- `.exe`、`.obj`、`.pdb`；
- checkpoint 和 formal 中间结果。

需要提交的小型基准结果、fixture、hash 摘要、配置文件或审计摘要，必须在 Stage 计划中明确列出。

## 15. 统一审计脚本和 Hook

项目应优先使用统一审计脚本，而不是每个 Stage 重写 Git 审计逻辑。建议路径：

```text
Task/Common/scripts/stage_audit.py
```

统一审计脚本负责检查：

- 当前分支不是 `main`；
- `manifest.json` 中的 functional range 与真实 Git diff 一致；
- `Task/Common/Plan/`、`build/`、`results/`、`.exe`、`.obj`、`.pdb` 未进入提交；
- `Task/BCH/`、`Task/CC/`、`Task/LDPC/` 未越界进入当前 Stage；
- `validation_report.md` 无 `Pending`、`NOT_PUSHED` 等冲突状态；
- 远程分支包含被审计的功能提交；
- `mergeStatus` 为 `NOT_MERGED`。

Git hook 只允许检查，不得自动修改文件。

- pre-commit 建议检查：当前不在 `main`、禁止目录和生成产物未 staged、当前 Stage checker 通过、manifest 与 functional range 一致。
- pre-push 建议检查：目标不是 `main`、Stage Gate 为 PASS、本地无意外 staged/unstaged 混乱、远程分支名称正确。
- 禁止使用 `--no-verify` 绕过项目 hook，除非用户明确授权。
