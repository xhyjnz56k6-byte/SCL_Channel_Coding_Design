# Codex Git 主线与分支工作流约束

> 适用仓库：`SCL_Channel_Coding_Design`  
> 适用对象：Codex、本地开发者、后续 GitHub 审查流程  
> 目标：保证每个 Stage 的修改可追踪、可复现、可审查，并避免未经验证的代码污染 `main` 主线。

---

## 1. 核心概念

### 1.1 `main` 主线

`main` 是项目唯一正式稳定主线，只允许包含：

- 已完成且已经通过测试的阶段；
- 已通过人工审查或 GPT/GitHub 差异审查的代码；
- 已生成完整变更记录和验证报告的提交；
- 随时可以用于演示、复现或继续开发的稳定版本。

`main` 中禁止出现：

- 未完成代码；
- 尚未编译的代码；
- smoke 未通过的代码；
- 临时调试输出；
- 未说明用途的批量修改；
- 尚未确认正确的实验结果；
- Codex 自动合并的未经审查内容。

可将 `main` 理解为：

> 老师随时要求查看或演示时，可以直接使用的正式版本。

---

### 1.2 Stage

Stage 是项目管理中的独立任务阶段，例如：

- `stage04_bch15_encoder`
- `stage05_bch15_decoder`
- `stage23_cc_hard_viterbi`
- `stage44_ldpc_layered_spa`

一个 Stage 必须有明确边界，只完成一个清晰任务。

例如 `stage04_bch15_encoder` 只允许完成：

- BCH(15,11,1) 编码器；
- 对应单元测试；
- MATLAB 编码结果对比；
- 本阶段说明文档。

禁止顺手实现：

- BCH 译码器；
- AWGN formal；
- 卷积码；
- LDPC；
- 下一 Stage 的内容。

---

### 1.3 Branch 分支

一个 Stage 原则上对应一个独立 Git 分支。

命名格式：

```text
stageXX-short-description
```

示例：

```text
stage04-bch15-encoder
stage05-bch15-decoder
stage23-cc-hard-viterbi
stage44-ldpc-layered-spa
```

分支是从最新稳定 `main` 上创建的临时开发路线。

分支中的代码即使失败，也不能影响 `main`。

---

### 1.4 Commit

Commit 是分支中的一次版本存档。

一个 Stage 分支可以包含多个 commit，例如：

```text
stage04-bch15-encoder
├─ commit 1：建立接口
├─ commit 2：实现编码器
├─ commit 3：增加测试
└─ commit 4：修复 MATLAB bit-order mismatch
```

所有 commit 经验证和审查后，才能把整个 Stage 合并进 `main`。

---

## 2. 主线与分支的关系

示意图：

```text
main
A ─── B ─── C
              \
               D ─── E
          stage04-bch15-encoder
```

其中：

- A、B、C：已经合入 `main` 的稳定阶段；
- D、E：Stage04 分支中的开发和修复提交。

Stage04 通过后：

```text
main
A ─── B ─── C ─── D ─── E
```

然后从新的 `main` 创建下一阶段分支。

---

## 3. 分支不是另一个文件夹

Git 分支不是手工复制出来的工程目录。

本地工程仍然只有一个：

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design
```

切换分支时，Git 会自动更新该目录中的文件。

查看当前分支：

```powershell
git branch --show-current
```

查看全部本地分支：

```powershell
git branch
```

星号 `*` 表示当前所在分支。

禁止手工创建：

```text
SCL_Channel_Coding_Design_main
SCL_Channel_Coding_Design_stage04
```

以免两个工程副本相互混淆。

---

## 4. 每个 Stage 的标准 Git 流程

### 4.1 开始前必须回到主线

```powershell
cd C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design

git switch main
git pull
git status
```

必须确认：

```text
On branch main
nothing to commit, working tree clean
```

若工作区不干净，禁止直接创建新 Stage 分支。

---

### 4.2 从最新 `main` 创建 Stage 分支

示例：

```powershell
git switch -c stage04-bch15-encoder
```

确认：

```powershell
git branch --show-current
```

期望输出：

```text
stage04-bch15-encoder
```

Codex 必须先确认当前不在 `main`，才能修改代码。

---

### 4.3 Codex 只完成当前 Stage

Codex 修改前必须明确：

- 当前 Stage 名称；
- 当前分支名称；
- 本阶段目标；
- 本阶段不做什么；
- 允许修改的目录；
- 禁止修改的目录；
- 需要运行的测试；
- Gate 名称。

若当前分支为 `main`，Codex必须停止并要求先创建 Stage 分支。

---

### 4.4 修改后必须检查差异

至少执行：

```powershell
git status
git diff --stat
git diff
```

必须核对：

- 是否只修改了当前 Stage 允许范围；
- 是否误改 BCH、CC、LDPC 的其他目录；
- 是否误改公共数据；
- 是否新增了大文件或编译产物；
- 是否删除了旧 Stage 或旧结果；
- 是否存在未解释的格式化改动。

---

### 4.5 测试通过后才允许 commit

允许 commit 的最低条件：

- 编译成功；
- 当前 Stage 单元测试通过；
- 无噪声或固定输入验证通过；
- MATLAB 对比已通过，或明确记录尚未执行及原因；
- 旧功能回归测试通过；
- `changed_files.md` 已生成；
- `validation_report.md` 已生成；
- `manifest.json` 已生成；
- `changes.patch` 已生成；
- 当前 Gate 状态明确。

---

### 4.6 提交时禁止无差别 `git add .`

优先按明确文件或逻辑组暂存，例如：

```powershell
git add Task\BCH\segmented\current\include\bch15_encoder.h
git add Task\BCH\segmented\current\src\bch15_encoder.cpp
git add Task\BCH\segmented\current\tests\test_bch15_encoder.cpp
git add Task\BCH\segmented\stages\stage04_bch15_encoder
```

然后检查：

```powershell
git diff --cached --stat
git diff --cached
```

提交：

```powershell
git commit -m "stage04: implement BCH(15,11) encoder"
```

Commit message 建议格式：

```text
stageXX: concise description
```

---

### 4.7 推送 Stage 分支

```powershell
git push -u origin stage04-bch15-encoder
```

Codex允许：

- commit 当前 Stage 分支；
- push 当前 Stage 分支。

Codex禁止：

- 自动合并到 `main`；
- 自动删除远程分支；
- 自动 force push。

---

### 4.8 GitHub / GPT 审查方式

审查时比较：

```text
main
vs.
stage04-bch15-encoder
```

推荐审查请求：

> 请比较 `stage04-bch15-encoder` 分支与 `main` 分支的差异，重点审查 BCH 编码器实现、测试覆盖、MATLAB 对比、变更范围以及是否存在越界修改。

若发现问题，继续在原 Stage 分支修改、测试、commit、push。

禁止在问题未解决时合并主线。

---

### 4.9 审查通过后由用户决定合并

Codex默认不得执行以下操作。

由用户确认后，再运行：

```powershell
git switch main
git pull
git merge --no-ff stage04-bch15-encoder
git push origin main
```

使用 `--no-ff` 保留该 Stage 的独立分支历史。

---

### 4.10 分支合并后的清理

合并成功且确认远程 `main` 正常后，可以删除分支：

```powershell
git branch -d stage04-bch15-encoder
git push origin --delete stage04-bch15-encoder
```

删除分支不会删除已经合入 `main` 的代码和 commit。

---

## 5. Stage 失败时的处理

只要未合并进 `main`，失败分支不会污染主线。

返回主线：

```powershell
git switch main
```

若确认废弃：

```powershell
git branch -D stage04-bch15-encoder
git push origin --delete stage04-bch15-encoder
```

重新开始：

```powershell
git switch -c stage04-bch15-encoder-v2
```

禁止为挽救失败分支而对 `main` 执行危险重置。

---

## 6. 同时开发多个 Stage 的限制

本项目原则上采用串行 Stage 流程：

```text
Stage04 完成并合并
↓
创建 Stage05
↓
Stage05 完成并合并
↓
创建 Stage06
```

避免同时打开多个依赖关系复杂的 Stage。

若分支期间 `main` 更新，需要同步：

```powershell
git switch main
git pull

git switch stage05-bch15-decoder
git merge main
```

同步后必须重新运行测试。

---

## 7. 每个 Stage 必须生成的审计文件

每个 Stage 目录统一包含：

```text
stageXX_name/
├─ stage_plan.md
├─ changed_files.md
├─ validation_report.md
├─ manifest.json
├─ changes.patch
├─ frozen_config.csv
├─ commands_used.md
├─ git_commit.txt
├─ known_issues.md
└─ snapshot/
```

### 7.1 `stage_plan.md`

必须记录：

- Stage 目标；
- 非目标；
- 输入和输出；
- 允许修改范围；
- 禁止修改范围；
- 测试计划；
- Gate 条件；
- 停止边界。

### 7.2 `changed_files.md`

每个文件至少记录：

- 工程相对路径；
- 新增、修改或删除；
- 文件作用；
- 修改原因；
- 关键函数或关键位置；
- 是否改变原有行为；
- 与当前 Stage 的关系。

推荐格式：

```markdown
## Added Files

### `Task/CC/block/current/src/viterbi_hard.cpp`

- 类型：新增
- 作用：实现 64 状态硬判决 Viterbi
- 关键位置：
  - 分支度量
  - ACS 更新
  - 回溯
- 所属模块：CC / block / decoder
- 是否影响旧功能：否
```

不要依赖固定行号作为唯一定位方式，因为后续修改会导致行号变化。应同时写：

- 函数名；
- 类名或结构体名；
- 代码块作用；
- 必要时再附当前行号范围。

### 7.3 `validation_report.md`

至少记录：

- 编译命令和结果；
- 单元测试结果；
- 无噪声结果；
- MATLAB 对比结果；
- 回归测试结果；
- 未通过项；
- Gate 状态。

### 7.4 `manifest.json`

机器可读示例：

```json
{
  "stage": "stage17_cc_hard_viterbi",
  "branch": "stage17-cc-hard-viterbi",
  "added": [
    "Task/CC/block/current/include/viterbi_hard.h",
    "Task/CC/block/current/src/viterbi_hard.cpp"
  ],
  "modified": [
    "Task/CC/block/current/src/cc_main.cpp"
  ],
  "deleted": [],
  "tests": [
    "test_hard_viterbi_noiseless",
    "test_hard_viterbi_matlab"
  ],
  "gate": "PASS_STAGE17_CC_HARD_VITERBI"
}
```

### 7.5 `changes.patch`

保存本阶段相对 `main` 的补丁：

```powershell
git diff main...HEAD > Task\...\stageXX_name\changes.patch
```

### 7.6 `git_commit.txt`

记录：

```text
stage:
branch:
commit:
parent:
commit_message:
remote:
push_status:
```

若生成该文件后又产生新的 commit，应更新为最终 commit hash。

### 7.7 `known_issues.md`

必须如实记录：

- 尚未执行的测试；
- 当前限制；
- 已知不一致；
- 临时措施；
- 后续 Stage 才解决的问题。

禁止把未完成项写成已完成。

---

## 8. Codex 的危险 Git 操作禁令

除非用户明确逐条授权，否则 Codex禁止执行：

```text
git reset --hard
git clean -fd
git clean -fdx
git push --force
git push --force-with-lease
git rebase main
git rebase -i
git commit --amend
git filter-branch
git filter-repo
删除或重写历史 commit
直接在 main 修改或提交
自动 merge 到 main
删除旧 Stage
覆盖旧实验结果
```

Codex也不得：

- 自动解决含义不明确的 merge conflict；
- 将大量生成结果提交到 GitHub；
- 将 `.exe`、`.obj`、`.pdb` 等编译产物提交 Git；
- 修改 `.gitignore` 来隐藏本应审查的源码或报告；
- 为让测试“通过”而删除失败测试。

---

## 9. Codex 默认停止点

Codex默认执行到：

```text
代码修改完成
→ 测试完成
→ 审计文件完成
→ Stage 分支 commit 完成
→ Stage 分支 push 完成
→ 停止
```

Codex不得自动执行：

```text
merge main
```

最终是否合并，必须由用户在审查后决定。

若当次任务未明确要求 push，则默认停止在：

```text
修改、测试和审计完成，尚未 commit/push
```

---

## 10. 每次任务开始时 Codex 必须完成的自检

Codex开始修改前必须报告：

1. 当前仓库根目录；
2. 当前分支；
3. 当前 `git status`；
4. 当前 Stage；
5. 当前 Stage 允许修改的目录；
6. 当前 Stage 禁止修改的目录；
7. 将运行的测试；
8. 是否会 commit；
9. 是否会 push；
10. 明确声明不会 merge `main`。

若当前分支为 `main`，Codex必须停止代码修改。

---

## 11. 每次任务结束时 Codex 必须输出

1. 当前分支；
2. 最终 commit hash；
3. 是否已 push；
4. 新增文件列表；
5. 修改文件列表；
6. 删除文件列表；
7. 测试结果；
8. Gate 结果；
9. 未完成事项；
10. GitHub 审查时应比较的分支；
11. 明确说明未合并 `main`。

---

## 12. 如何让 Codex 每次自动遵守，而不是反复写提示词

### 12.1 在仓库根目录创建 `AGENTS.md`

将最重要、每次都必须执行的规则写入：

```text
SCL_Channel_Coding_Design/
└─ AGENTS.md
```

Codex会在开始工作前读取 `AGENTS.md`。仓库根目录的文件适合保存整个项目长期有效的约束。

建议根目录 `AGENTS.md` 保持简洁，只放不可违反的硬规则，并引用本文件。

推荐内容：

```markdown
# Repository Instructions

## Mandatory Git workflow

- Read `初始规划/CODEX_GIT_WORKFLOW.md` before modifying files.
- Never modify or commit directly on `main`.
- Each task must use one `stageXX-*` branch created from the latest clean `main`.
- One branch may only implement one clearly defined Stage.
- Before editing, report repository root, current branch, `git status`, allowed scope, forbidden scope, test plan, commit plan, and push plan.
- If the current branch is `main`, stop and request creation of a Stage branch.
- Do not merge to `main`; only the user may approve merging.
- Do not run destructive Git commands, force push, rebase `main`, rewrite history, delete prior stages, or overwrite prior results.
- Before commit, run required tests and generate:
  - `stage_plan.md`
  - `changed_files.md`
  - `validation_report.md`
  - `manifest.json`
  - `changes.patch`
  - `git_commit.txt`
  - `known_issues.md`
- Commit and push only the current Stage branch when the user requested it.
- At completion, report branch, commit, push status, changed files, tests, gate, known issues, and confirm that `main` was not merged.

## Project scope

- Use basic, readable C++ without heavy third-party libraries or unnecessarily complex language features.
- Preserve algorithm performance and correctness.
- Python may drive build, tests, data preparation, result checks, and plotting; core encoding and decoding algorithms remain C++.
- Keep BCH, CC, and LDPC code, scripts, build outputs, and results inside their respective directories.
- `Task/Common` contains only genuinely shared frame pools, Gaussian mother-noise policy, seed rules, and shared formats.
```

### 12.2 将完整规则文件提交到仓库

建议把本文件保存为：

```text
初始规划/CODEX_GIT_WORKFLOW.md
```

根目录 `AGENTS.md` 只放摘要和入口，完整细节保存在该文件中。

这样可以同时做到：

- `AGENTS.md` 足够短，不容易因上下文过长而被截断；
- 完整流程可以人工阅读；
- 修改规则有 Git 历史；
- Codex每次知道应先读取哪个文件。

### 12.3 必要时设置目录级 `AGENTS.md`

可在专用目录放置更具体的规则，例如：

```text
Task/BCH/AGENTS.md
Task/CC/AGENTS.md
Task/LDPC/AGENTS.md
```

示例：

```markdown
# BCH-specific instructions

- Do not modify CC or LDPC directories.
- Segmented BCH and block BCH must keep independent scripts, build, results, stages, and configs.
- MATLAB comparison is mandatory before formal simulation.
```

目录越接近当前工作区，越适合放局部约束。

### 12.4 重新启动 Codex 会话以加载新规则

`AGENTS.md` 通常在一次 Codex 运行或会话开始时加载。

新增或修改后，应：

- 重新启动 Codex 会话；
- 或重新运行 Codex；
- 然后让 Codex列出当前加载的指令来源。

推荐验证命令：

```powershell
codex --ask-for-approval never "Summarize the current repository instructions and list the instruction files you loaded."
```

若从特定子目录启动：

```powershell
codex --cd Task\BCH --ask-for-approval never "Show which instruction files are active."
```

### 12.5 使用 Git Hook 做硬性阻止

`AGENTS.md` 是持续指导，不是绝对技术锁。

建议配合 Git hook，阻止在 `main` 上直接 commit。

`.git/hooks/pre-commit` 可检查：

```bash
#!/bin/sh

branch="$(git branch --show-current)"

if [ "$branch" = "main" ]; then
  echo "ERROR: Direct commits on main are forbidden."
  echo "Create and switch to a stageXX-* branch first."
  exit 1
fi

case "$branch" in
  stage[0-9][0-9]-*)
    ;;
  *)
    echo "ERROR: Branch must follow stageXX-description naming."
    exit 1
    ;;
esac
```

Windows 项目可通过 Git Bash 执行该 hook。

注意：`.git/hooks` 默认不会随 Git 仓库提交。更好的做法是把受版本控制的 hook 放在：

```text
.githooks/pre-commit
```

然后执行一次：

```powershell
git config core.hooksPath .githooks
```

这样所有成员和 Codex都使用仓库内的 hook。

### 12.6 GitHub 主线保护

在 GitHub 仓库设置中保护 `main`：

- 禁止直接 push 到 `main`；
- 要求通过 Pull Request 合并；
- 要求至少一次审查；
- 要求状态检查通过；
- 禁止 force push；
- 禁止删除 `main`。

这样即使 Codex误操作，也难以直接污染远程主线。

### 12.7 自动检查脚本

建议增加：

```text
scripts/check_git_policy.py
```

检查：

- 当前是否在 `stageXX-*` 分支；
- 工作区是否存在越界修改；
- Stage 审计文件是否齐全；
- 是否存在未跟踪的大文件；
- 是否修改了不允许的目录；
- 是否生成了 patch；
- Gate 是否为 PASS。

Codex提交前必须运行：

```powershell
python scripts\check_git_policy.py
```

### 12.8 推荐的三层约束

最稳妥的组合是：

```text
第一层：AGENTS.md
持续告诉 Codex 应该怎么做

第二层：检查脚本与 Git hooks
在本地阻止明显违规操作

第三层：GitHub branch protection / PR
在远程阻止未经审查的代码进入 main
```

不要只依赖提示词，也不要只依赖 `AGENTS.md`。

---

## 13. 推荐仓库结构

```text
SCL_Channel_Coding_Design/
│
├─ AGENTS.md
├─ .githooks/
│  └─ pre-commit
│
├─ 初始规划/
│  ├─ CODEX_GIT_WORKFLOW.md
│  └─ project_progress.md
│
├─ Task/
│  ├─ Common/
│  ├─ BCH/
│  │  └─ AGENTS.md
│  ├─ CC/
│  │  └─ AGENTS.md
│  └─ LDPC/
│     └─ AGENTS.md
│
└─ scripts/
   └─ check_git_policy.py
```

若项目约束要求 `scripts` 不放在三种码之外，则全局 Git 检查脚本可以改放：

```text
初始规划/git_tools/check_git_policy.py
```

或者只保留在：

```text
.githooks/
```

编码仿真相关脚本仍必须放回 BCH、CC、LDPC 各自目录。

---

## 14. 最简强制规则

Codex只需要记住以下六条：

1. `main` 只保存经过验证和审查的稳定代码。
2. 每个 Stage 必须从最新、干净的 `main` 创建独立 `stageXX-*` 分支。
3. Codex只能在 Stage 分支修改，禁止直接修改、提交或 push `main`。
4. 修改后必须测试并生成完整审计文件。
5. Codex可按授权 commit/push Stage 分支，但禁止自动 merge `main`。
6. 最终是否合并由用户在 GitHub/GPT 审查后决定。

固定流程：

```text
main 稳定主线
→ 创建 stageXX 独立分支
→ Codex 修改
→ 编译和测试
→ 生成审计文件
→ commit/push 分支
→ GitHub/GPT 审查
→ 用户决定是否 merge
```
