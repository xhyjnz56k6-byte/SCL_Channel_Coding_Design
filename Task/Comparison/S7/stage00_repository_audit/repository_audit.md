# S7 Stage00 仓库审计

## 审计时间与仓库状态

- 日期：2026-08-04（Asia/Shanghai）。
- 仓库根目录：`C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design`。
- 当前分支：`S7-Comparision`，跟踪 `origin/S7-Comparision`。
- 审计起点 HEAD：`d01b366ea84d38cc73c7b11cc9a7534446987ac2`。
- 审计前工作区：干净，无 staged、unstaged 或未跟踪修改。
- 与 `main` 的关系：从 `07891b71db154aacad0aabf1d795f0bc0e299581` 分出，领先 1 个提交。
- 审计前 `main...HEAD` 差异：仅新增 `初始规划/S7-Plan.md`。

## 分支与目录结论

用户明确指定继续使用 `S7-Comparision`。该名称不符合项目建议的 `stageXX-short-description` 格式且保留 `Comparision` 拼写，作为已授权例外记录，不改名、不重建分支。

仓库不存在 `Task/S7`，但存在 `Task/Comparison/S5` 和 `Task/Comparison/S6`。根据任务提示“或仓库现有对应的 S7 目录组织”，S7 唯一工作目录冻结为 `Task/Comparison/S7`。

## 允许与禁止范围

允许新增或修改 `Task/Comparison/S7/**`。禁止修改或删除 `Task/BCH/**`、`Task/CC/**`、`Task/LDPC/**`、`Task/Common/**`、`Task/Comparison/S5/**`、`Task/Comparison/S6/**` 以及旧结果。公共源码只读复用；如必须改动，先停止并申请授权。

## 可复用依赖

- BCH：`Task/BCH/segmented/current` 包含 BCH(15,11,1) encoder、syndrome、lookup table、lookup decoder 和 segmented adapter。
- BCH 仿真：`Task/BCH/simulation/current` 包含 AWGN adapter、runner 和无噪声/指标测试。
- CC：`Task/CC/shared` 包含 trellis；`Task/CC/block/current` 包含 block encoder、hard/soft Viterbi。
- Common：帧池、随机策略、标准高斯噪声、BPSK、AWGN、demodulation、统计、停止和 checkpoint 接口。
- S5：`Task/Comparison/S5/current` 包含共享随机性、多信道 runner、结果 checker 和 MATLAB fixed reference。
- S6：包含固定译码方案、计时口径、结果 inventory 和独立历史基线。

## LDPC 历史基线审计

- 直接来源：`Task/Comparison/S6/results/ldpc/ldpc_n560_integrated_results.csv`。
- inventory 记录：62 行，41224 bytes，SHA256 `66135340c79acfb05e68615eccdc75d699b7c38b3970ddb668a06d5c7b455d18`。
- 上游来源：Stage23 修订后的 N560 Formal 点表，由 S6 整合。
- 参数：Direct BG2，K=300、N=560、Zc=56、filler=148、parity=112、maxIter=32；BP 与 NMS，NMS alpha=0.95。
- 信道：普通 BPSK+AWGN；31 个 Es/N0 点。
- 限制：未包含 S7 未知连续 BPSK 极性反转、六位置、三突发比例或严格 S7 pair-stop，因此不兼容主 Formal。只能进入独立历史参考表，不参与交织收益或突发容限结论。

## 工具与历史风险

- Python 3.11.0 可用。
- CMake 4.4.0 可用。
- MATLAB 命令和工具箱必须在 Stage08 前通过真实命令验证；当前不标记 PASS。
- 仓库历史已跟踪部分 build、exe、obj、pycache 等生成内容。S7 不删除旧历史，但自己的 checker 必须阻止此类新文件进入提交。

## Stage00 Gate

- PASS：仓库根目录、分支、HEAD 和工作区状态已记录。
- PASS：S7 目录和写入边界已冻结。
- PASS：BCH、CC、Common、S5、S6 依赖路径已定位。
- PASS：LDPC 历史来源、参数、信道兼容性和限制已记录。
- PASS：未修改既有编码目录，未运行 Formal，未 commit、未 push、未合并 main。
- NOT_TESTED：MATLAB 运行环境；安排在 Stage08 前实测。

Stage00 总状态：PASS（MATLAB 属于后续 Stage08 Gate，不冒充已通过）。

