# S7 交织抗连续突发错误实验设计计划

## 1. 背景与原始要求

S7 在 S1～S6 已验证的编译码、公共随机源、信道和统计框架上，固定代表性 BCH 与卷积码方案，研究交织方式、交织跨度、突发比例和突发位置对 BER、FER、连续突发容限及工程代价的影响。LDPC 不配置交织，只保留独立历史参考。

结果必须回答三项问题：能容忍多长的连续突发、FER 改善多少、为此增加多少缓冲和 CPU 处理开销。

## 2. 与 S1～S6 的关系

- 复用 `Task/BCH/segmented/current` 的 BCH(15,11,1) 编码、syndrome 与查表译码。
- 复用 `Task/CC/shared` 和 `Task/CC/block/current` 的 K=7、171/133 trellis、整块编码和软判 Viterbi。
- 只读复用 `Task/Common` 的帧、标准高斯噪声、随机策略、BPSK、统计和 checkpoint 语义。
- 参考 S5 的共享随机量、信道组织、成组停止和结果审计框架。
- 采用 S6 已冻结的主译码方案和纯译码计时口径。
- S7 不改变任何 S1～S6 历史结果的含义；若复用接口不足，停止并申请扩大修改范围。

## 3. 目标、非目标与目录边界

目标包括 Stage00～Stage09 的审计、规格冻结、交织器、主突发信道、BCH/CC 链路、C++/MATLAB Smoke、参数预扫描与 Formal 候选排名。

非目标：重新扫描码型、修改稳定算法、将不同码型混为交织收益、伪造物理时延、在人工确认前运行 Formal、生成正式科研结论或合并 `main`。

唯一写入范围为 `Task/Comparison/S7/**`。`Task/BCH`、`Task/CC`、`Task/LDPC`、`Task/Common`、S5 和 S6 均为只读依赖。

## 4. 固定编码方案

### 4.1 BCH

- payload：200 bit；补齐到 209 bit。
- 组织：19×BCH(15,11,1)，每个子码字 15 bit。
- 发送长度：285 bit；实际码率 `200/285`。
- BPSK、硬判决、综合校验查表译码。
- 解交织后恢复原始 19 个子码字边界；去除填充后只统计 200 bit payload。

固定 S200 是为了直接观察连续错误在 19 个独立 t=1 纠错单元之间的分散机制，而不是重新比较整块 BCH。

### 4.2 卷积码

- payload：300 bit；K=7；生成多项式 171/133（八进制）。
- 母码率 1/2，不打孔；添加 6 个清零尾比特。
- 306 个 trellis step，612 个发送 bit；实际码率 `300/612`。
- 解交织对象为 LLR；解交织后进入整块浮点软判 Viterbi。
- 去除尾比特后只统计 300 bit payload。

固定母码率避免把打孔位置、去打孔可靠度和突发与打孔图样对齐效应混入交织收益。

### 4.3 LDPC 历史基线

来源：`Task/Comparison/S6/results/ldpc/ldpc_n560_integrated_results.csv`，其上游为 Stage23 修订后的 N560 Formal 点表。

参数：Direct BG2，K=300、N=560、Zc=56、filler=148、parity=112、maxIter=32；BP/NMS，NMS alpha=0.95；31 个 Es/N0 点，每算法 31 行，共 62 行。

该数据使用普通 BPSK+AWGN，没有 S7 的未知连续极性反转、相同突发位置或严格 S7 成组停止，因此信道不兼容。它只能进入独立参考表，不能进入交织收益排名、突发容限计算或 BCH/CC 的统一性能结论。

## 5. 信道范围与数学定义

主 Formal 唯一信道为 `AWGN_CONTIGUOUS_BPSK_POLARITY_REVERSAL`：

`0 -> +1`，`1 -> -1`，且 `y[k] = h[k] x[k] + n[k]`。突发区间内 `h[k]=-1`，其他位置 `h[k]=+1`；`n[k]` 为独立 AWGN。接收机不知道突发区间，`receiverKnowsBurst=false`，突发不绕回。

极性反转必须发生在 BPSK 调制之后，不能通过调制前翻转编码 bit 或生成 LLR 后乘 -1 代替主实现。BCH 对接收符号硬判决后解交织；CC 根据接收符号和噪声方差形成 LLR 后解交织。

已知连续擦除、未知连续强干扰不进入主 Formal。它们只允许作为带独立命名、独立配置和独立结论的 Smoke/扩展工程验证；若 Stage09 前未实现，必须在 `known_issues.md` 明确记录为未做项。

`L=0` 必须严格退化为普通 AWGN；全帧反转只做测试，不作为正式主点。

## 6. 突发比例、位置与公平性

- 比例：2%、5%、10%；`L=round(ratio*Ntx)`。
- 位置：HEAD、QUARTER、MIDDLE、THREE_QUARTER、TAIL、RANDOM。
- 起点分别为 `0`、`round((N-L)/4)`、`round((N-L)/2)`、`round(3(N-L)/4)`、`N-L`，以及由 frameIndex 和固定 seed 在 `[0,N-L]` 确定生成的随机起点。
- 记录 requested/actual ratio、encodedLength、burstStart、burstEnd、positionType、wrapAround=false。

同一编码、Es/N0、突发比例、位置、frameIndex 的比较组共享 payload、母标准高斯样本、突发起点和停止帧集合。记录 payloadChecksum、noiseChecksum、burstStartChecksum、mappingHash、decodedPayloadChecksum 和 frameSequenceHash。

## 7. BCH 交织方法与公平比较

### 7.1 方法定义

- `NONE`：恒等置换。
- `BCH_CODEBLOCK`：以 BCH 子码字为行，D 行×15 列，按行写入、按列读出；D=4、8、16、19；末组按实际行数处理。
- `ROW_COLUMN`：对 285 bit 全帧按行写、按列读，空格跳过且不发送 padding；候选行数 4、8、15、19。
- `GLOBAL_PSEUDORANDOM`：对 0～284 做固定 seed 的全排列，记录 SHA256；不把它解释为传统“深度”。
- 旧 S2 rotating segment 只能命名为 `LEGACY_ROTATING_BLOCK` 并归档，不进入正式方法图例。

### 7.2 两层比较原则

第一层是等跨度公平对比：只有有效交织跨度、参与 bit 数或缓冲窗口等价的方案才能解释为“方法差异”。局部方案与全帧方案若无法严格等跨度，只报告为工程配置对比，并明确跨度/缓冲量不同。

第二层是方法内部敏感性：BCH_CODEBLOCK 比较 D，ROW_COLUMN 比较 rows，伪随机方案仅比较明确定义的局部跨度扩展（若实现）或固定全帧方案，不把 D=4 与全帧伪随机的差异归因于方法本身。

结果表必须同时给出 method、spanBits、bufferBits、rows、columns 和 fairnessGroupId。

## 8. 卷积码交织方法

- `NONE`：恒等置换。
- `SHORT_DEPTH_BLOCK`：单位为 trellis step；每个 `S_t=[c_t,0,c_t,1]` 始终成组。D=4、8、16，C=8；窗口为 D×C 个 trellis step，末窗口按实际长度处理。
- `PSEUDORANDOM`：冻结 `permutationUnit=TRELLIS_STEP`、`preserveMotherOutputPair=true`；span=32、64、128 trellis steps。每个局部窗口内对 trellis-step 索引做固定 seed 排列，末窗口按实际长度生成合法置换并记录 hash。

严禁拆散同一 trellis step 的两个母码输出。

## 9. C++/MATLAB 固定约定

- bit 顺序：payload 和码字均按文件/向量索引从 0 到 N-1；每行 trace 显式记录零基索引。
- trellis 状态编号：6 个存储单元按二进制寄存器内容编号 0～63；状态 0 为全零；状态转移和寄存器位方向由固定向量锁定。
- 生成多项式输出顺序：每个 trellis step 先输出 171，再输出 133，即 `[c_t,0,c_t,1]`。
- Viterbi tie-break：候选路径度量完全相等时选择 predecessor state 编号较小者；若仍相等，选择输入 bit 0。
- traceback：终止卷积码从最终状态 0 开始；不允许自动选择最小终态替代。
- BCH syndrome：15 bit 接收码字按索引 0～14 固定多项式方向；syndrome 数值和查表 key 采用现有 `bch15_syndrome`/lookup 实现的固定向量输出，C++ 与 MATLAB 必须逐项一致。
- BCH 查表索引：零 syndrome 对应“无更正”；非零 syndrome 以规范化整数 key 查找错误掩码，错误位索引保持零基 trace 约定。

Stage08 必须比较 payload、编码 bit、置换、BPSK、burst mask、标准高斯样本、接收符号、硬判/LLR、syndrome、路径度量、最终 payload 和 BER/FER 计数。

## 10. Es/N0、停止与 checkpoint

- Es/N0：-5.0～10.0 dB，步长 0.5 dB，共 31 点。
- `sigmaSquared=1/(2*10^(EsN0Db/10))`。
- minFrames=1000，targetFrameErrors=200，maxFrames=50000，checkpointIntervalFrames=1000。
- 同组所有方案至少完成 1000 帧；所有方案均达到 200 错误帧或共同达到 50000 帧时停止；同组 framesProcessed 必须完全相同。
- checkpoint 保存冻结配置 hash、case key、下一 frameIndex、累计计数、计时采样状态和共享序列 hash；恢复后不得重复或跳过帧。

## 11. 计时与结构等待量

纯译码时间从解交织后的完整 decoder input 就绪开始，到 payload、尾比特处理和状态返回完成为止。它不含交织、信道、AWGN、硬判/LLR 生成、解交织、I/O、日志、哈希或 checkpoint。

分别统计 decode mean/median/p95/p99/max，以及 interleave/deinterleave mean/p95/max；`T_add_cpu=T_interleave_cpu+T_deinterleave_cpu`。

结构代价输出 bufferBits、startupDelayBits、bufferFractionOfFrame、startupDelayTrellisSteps、spanBits、rows、columns。没有符号率和采样率，禁止换算成物理时间。

## 12. BER、FER 与改善指标

原始 CSV 保存错误 bit/frame 计数以及 BER、FER。改善指标包括绝对改善、相对降低率、改善倍数和目标 FER 可插值区间内的 Es/N0 改善。基线 FER 为 0 时，相对指标不得伪造。

候选排名不能只按平均 FER，必须联合考虑：平均/目标 FER、六位置最坏 FER、bufferBits/跨度和 deinterleave CPU 开销。Stage09 同时输出分项指标、归一化评分、Pareto 标记、排名依据和敏感性说明，不允许隐藏权重。

## 13. 高 SNR 零值策略

该策略同时写入 Smoke/Formal 配置和 Gate：

- 原始 CSV 保留 `BER=0`、`FER=0` 及真实 framesProcessed/errorCount。
- 对数图不绘制零值点，并在 figure-data 中标记 `plotted=false`、`exclusionReason=ZERO_ON_LOG_AXIS`。
- 禁止替换为任意伪小值，禁止从最后非零点延伸水平线。
- 正式图中禁止出现 error floor、零错上界水平线、箭头或文字标记。
- 零值后重新出现非零值时标记 `nonMonotonicHighSnrAnomaly`，阻止自动发布并要求审查。

## 14. 资产、归档与路径 Gate

- 每次修改已有结果前，将旧 CSV、PNG、manifest、report、checkpoint、figure-data 和 validation 移入当前 Stage 的 `archive/vNN_yyyymmdd_before_reason/`，并附中文 `readme.txt`；不得删除旧结果。
- 每个新增目录必须有 `readme.txt`。
- 每张正式图使用独立目录，至少包含 figure.png、figure_data.csv、plot_manifest.json、plot_validation.json、sha256.txt、readme.txt。
- 每图 readme 和 manifest 必须记录运行时解析的原始数据绝对路径及历史数据绝对路径；不得编造路径。
- checker 验证 readme 覆盖、归档命名、绝对路径存在性、图数据与原始 CSV 一致性及 SHA256。

## 15. Stage01～Stage16 计划

- Stage00：仓库、分支、历史结果和环境审计。
- Stage01：范围、schema、目录、资产与 Gate 冻结。
- Stage02：参数、术语、随机性、C++/MATLAB 约定及配置冻结。
- Stage03：BCH 交织器与等跨度/内部敏感性元数据。
- Stage04：CC trellis-step 交织器。
- Stage05：未知连续 BPSK 极性反转信道。
- Stage06：BCH 完整接收链、错误块统计和计时。
- Stage07：CC LLR 接收链、Viterbi 和计时。
- Stage08：C++/MATLAB 固定向量 Smoke 与一致性检查。
- Stage09：边界/位置 Smoke、参数预扫描、候选排名与 Formal 资源估算。
- Stage10：BCH Formal；必须等待人工确认。
- Stage11：CC Formal。
- Stage12：代表工作点全起点扫描。
- Stage13：时延与复杂度汇总。
- Stage14：FER 改善和推荐参数。
- Stage15：基于 Formal 原始 CSV 的科研绘图。
- Stage16：最终审计与集成。

Stage09 完成后创建 `S7_stage01_stage09_smoke_review.md`，报告 Formal 方案点数、比较组数、预计运行时间、磁盘占用、checkpoint 恢复方案、推荐参数、风险和 Gate，然后打印 `PAUSED_BEFORE_STAGE10_WAITING_FOR_HUMAN_CONFIRMATION` 并停止。

## 16. 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| BCH 四种交织 | Stage03 | 正逆置换、末组、无噪声恢复 | 重复/缺失/越界索引 | 逐 bit 精确恢复 |
| BCH 公平比较 | Stage03/09 | 等跨度组和内部参数扫描 | 将局部与全帧解释为纯方法差异 | fairnessGroupId 与跨度字段完整 |
| CC 三种交织 | Stage04 | trellis-step 成组与尾窗口 | 拆散输出对、非法跨度 | pair 保持且精确逆映射 |
| 主突发信道 | Stage05 | 固定向量、L=0、全帧反转 | 调制前翻 bit、绕回 | 反转发生于调制后且 L=0 等价 AWGN |
| BCH 链路 | Stage06 | 硬判→解交织→查表 | 顺序或子块边界错误 | 无噪声 payload 全等 |
| CC 链路 | Stage07 | LLR→解交织→软 Viterbi | 先硬判、错误 tie-break/终态 | 无噪声 payload 全等 |
| C++/MATLAB | Stage08 | 全链 trace 逐项比较 | mapping/hash/计数 mismatch | 离散量相同且浮点误差达标 |
| 公平性与停止 | Stage08/09 | checksum、frame hash、pair-stop | 重生成随机量、帧数不同 | 同组共享量与帧集合一致 |
| 参数排名 | Stage09 | FER/最坏位置/缓冲/开销联合排名 | 单指标或隐藏权重 | 报告、排名、Pareto 数据齐全 |
| 零值策略 | Stage01/02/09 | 原始 0 和 plot exclusion | 伪小值、水平延伸、error floor 标记 | checker 全部通过 |
| 资产审计 | 全 Stage | archive/readme/绝对路径/SHA | 缺 readme、覆盖旧结果 | 资产 Gate 全部通过 |
| Formal 暂停 | Stage09 | 点数、组数、时间、磁盘、恢复方案 | 自动启动 Stage10 | 人工确认前无 Formal 产物 |

## 17. 风险与人工确认点

- 历史仓库已有被跟踪的 build/二进制产物；S7 不清理旧历史，但禁止新增。
- MATLAB 可执行环境和工具箱能力须在 Stage00/08 实测，未执行不得声称 PASS。
- 已知擦除和强干扰不是主 Formal；未做时如实记录。
- 运行时间和磁盘估算必须由 Stage08/09 实测样本外推，并明确估算方法。
- Stage10、Formal 科研图、最终结论和任何 commit/push 都需要用户另行授权。

