# Changed Files

## Added Files

### `Task/Common/config/global_config.json`

- 类型：新增
- 作用：冻结全局数学定义、长度字段、BPSK、硬判决、AWGN、LLR、置信区间、零错误点、交织、覆盖和 trace 策略。
- 原因：后续 Common Stage 和三类编码仿真需要统一机器可读定义。
- 关键字段：`rateDefinition`、`lengthDefinitions`、`bpskMapping`、`awgnModel`、`interleaverPolicy`
- 是否影响旧行为：否，当前只新增定义。
- 与 Common-01 的关系：核心冻结配置。

### `Task/Common/config/seed_policy.json`

- 类型：新增
- 作用：冻结 `masterSeed`、`noiseGroupId`、每帧独立噪声、跨 SNR 复用标准高斯和 seed 排除字段。
- 原因：保证硬/软 Viterbi 与 BP/NMS 公平比较。
- 关键字段：`reuseNoiseAcrossSnr`、`noiseSeedFields`、`excludedNoiseSeedFields`
- 是否影响旧行为：否。
- 与 Common-01 的关系：核心冻结配置。

### `Task/Common/config/stop_rules.json`

- 类型：新增
- 作用：冻结 smoke、prescan、formal trial、formal 的停止参数和停止原因。
- 原因：后续实验必须使用一致停止逻辑。
- 关键字段：`stopLogic`、`stopReasons`
- 是否影响旧行为：否。
- 与 Common-01 的关系：核心冻结配置。

### `Task/Common/config/result_schema.json`

- 类型：新增
- 作用：冻结 point results、curve summary、metadata、checkpoint 和 trace 字段。
- 原因：后续输出、恢复和审计需要统一字段。
- 关键字段：`pointResultFields`、`curveSummaryFields`、`checkpointFields`
- 是否影响旧行为：否。
- 与 Common-01 的关系：核心冻结配置。

### `Task/Common/docs/*.md`

- 类型：新增
- 作用：提供人可读定义文档，覆盖公共仿真、指标、seed、命名、checkpoint 和术语。
- 原因：便于人工审查并避免后续阶段解释分歧。
- 关键章节：长度字段、码率、AWGN/LLR、payload-only 指标、噪声公平性、图片命名。
- 是否影响旧行为：否。
- 与 Common-01 的关系：核心冻结文档。

### `Task/Common/scripts/validate_common01_definition.py`

- 类型：新增
- 作用：实际检查 Common-01 定义文件、JSON 类型、码率样例、seed 排除、停止逻辑、文档一致性和负向测试。
- 原因：证明 Gate 不是手写 PASS。
- 关键入口：正常验证、`--negative-tests`
- 是否影响旧行为：否。
- 与 Common-01 的关系：Gate 验证脚本。

### `Task/Common/stages/stage01_common_definition/*`

- 类型：新增
- 作用：记录 Stage 计划、文件变化、验证结果、manifest、冻结配置摘要、命令、commit 状态、已知问题和 snapshot。
- 原因：满足 Stage 审计要求。
- 是否影响旧行为：否。
- 与 Common-01 的关系：审计证据。

## Modified Files

None.

## Deleted Files

None.

