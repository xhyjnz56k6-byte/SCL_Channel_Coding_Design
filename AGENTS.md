# SCL_Channel_Coding_Design 项目规则

## 1. 项目范围

本工程包含三类信道编码：

- `Task/BCH`：BCH 编码、译码与仿真；
- `Task/CC`：卷积编码、Viterbi 译码与仿真；
- `Task/LDPC`：BG2 Direct QC-LDPC、Layered BP 译码与仿真；
- `Task/Common`：公共帧池、标准高斯母噪声、随机种子和公共格式。

核心编译码算法使用基础、清晰的 C++ 实现。Python只负责驱动编译、测试、数据生成、结果检查和绘图；MATLAB用于独立参考验证。

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
- 每个 Stage 必须从最新且干净的 `main` 创建独立分支。
- 分支名称使用：

```text
stageXX-short-description
```

- 一个分支只能完成一个 Stage。
- Codex只有在用户要求时，才可 commit 和 push 当前 Stage 分支。
- Codex禁止自动合并到 `main`。
- 是否合并由用户在代码和 GitHub 差异审查后决定。

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

## 6. 测试要求

- 每个模块必须有独立测试。
- 编码器和译码器必须先通过无噪声测试。
- BCH 和卷积码必须与 MATLAB 官方函数对比。
- Direct LDPC 必须与相同 BG2 子矩阵的 MATLAB 独立参考实现对比。
- smoke 未通过，禁止进入 prescan。
- prescan 未通过，禁止进入 formal。
- 未实际执行的测试不得标记为 PASS。
- 出现 mismatch、NaN、Inf 或校验失败时，必须停止并记录原因。

## 7. Stage 记录

每个 Stage 至少生成：

```text
stage_plan.md
changed_files.md
validation_report.md
commands_used.md
known_issues.md
```

其中：

- `changed_files.md`：记录文件路径、修改类型、作用、原因和关键函数；
- `validation_report.md`：记录编译、测试、MATLAB 对比和 Gate 结果；
- `known_issues.md`：如实记录未完成项和已知问题。

## 8. 完成后报告

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

## 9. 禁止操作

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

## 10. 默认停止位置

Codex默认执行到：

```text
代码修改
→ 编译和测试
→ 生成 Stage 记录
→ 按用户要求 commit/push 当前分支
→ 停止
```

禁止自动合并 `main`，禁止自动开始下一 Stage。

## 冲突处理

如用户指令、`AGENTS.md`、当前 Stage 计划、分支名称、现有实现或老师任务要求之间存在冲突：

1. 不得自行选择解释；
2. 不得通过扩大任务范围解决；
3. 必须停止修改；
4. 列出冲突项及其影响；
5. 等待用户确认后继续。

## 以下目录属于实验资产或生成内容，默认不提交 Git：

- `build/`
- `results/`
- 大型公共帧池；
- 公共噪声文件；
- MATLAB 临时文件；
- `.exe`、`.obj`、`.pdb`；
- checkpoint 和 formal 中间结果。

需要提交的小型基准结果、配置文件和审计摘要，必须在 Stage 计划中明确列出。