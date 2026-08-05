# S7 Stage01～Stage09 Smoke 综合审查报告

## 1. 仓库、分支与提交

- 仓库：`C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design`。
- 分支：`S7-Comparision`，跟踪 `origin/S7-Comparision`。
- 功能开始前 HEAD：`d01b366ea84d38cc73c7b11cc9a7534446987ac2`。
- 本轮未 commit、未 push、未合并 `main`。
- 唯一写入目录：`Task/Comparison/S7`；既有 BCH、CC、LDPC、Common、S5、S6 保持只读。

## 2. Stage 状态

| Stage | 内容 | 真实输出 | Gate |
|---|---|---|---|
| Stage00 | 仓库与历史审计 | repository_audit.md、LDPC 来源/限制 | PASS |
| Stage01 | 范围、schema、资产、零值策略 | stage plan、Gate 冻结 | PASS |
| Stage02 | 编码、信道、交织、随机和对照约定 | Smoke/Formal JSON | PASS |
| Stage03 | BCH 四种交织器 | C++ mapping、hash、unit test | PASS |
| Stage04 | CC 三种 trellis-step 交织器 | pair-preserving mapping、unit test | PASS |
| Stage05 | 连续极性反转+AWGN 主信道 | channel vector、L=0/边界测试 | PASS |
| Stage06 | BCH 硬判接收链 | 无噪声多方法 payload 恢复 | PASS |
| Stage07 | CC LLR+软 Viterbi 链 | 无噪声多方法 payload 恢复 | PASS |
| Stage08 | C++/MATLAB 固定向量 | 72 项 comparison/validation | PASS |
| Stage09 | 参数预扫描与 Formal 估算 | 612 行、排名、选择报告 | PASS |

## 3. BCH 链路审查

链路为 BCH-S200 编码→交织→BPSK→调制后连续极性反转→AWGN→硬判→硬 bit 解交织→按原 19×15 边界查表译码→去填充。

NONE、BCH_CODEBLOCK、ROW_COLUMN、GLOBAL_PSEUDORANDOM 的映射均为无重复、无缺失、无越界的可逆置换；多方法无噪声 payload 200/200 bit 一致。BCH syndrome 和 15 个单 bit 查表索引由 MATLAB 独立参考逐项通过。

## 4. 卷积码链路审查

链路为 CC R1/2 编码→按 trellis step 交织→BPSK→主突发信道→生成 LLR→LLR 解交织→整块浮点软判 Viterbi→去除 6 个尾比特。

所有映射固定 `permutationUnit=TRELLIS_STEP`、`preserveMotherOutputPair=true`。NONE、SHORT_DEPTH_BLOCK、PSEUDORANDOM 多方法无噪声 payload 300/300 bit 一致，traceback final state=0。

## 5. 主信道审查

极性反转真实发生在 BPSK 调制后；接收机未知突发，突发不绕回。L=0 严格退化为无附加损伤 AWGN；全帧反转固定向量通过；wrapAround 被拒绝。BCH 使用硬判后解交织，CC 使用 LLR 解交织后软判 Viterbi。

已知连续擦除和未知连续强干扰未实现，按冻结范围记录为扩展未做项，不进入主 Formal。

## 6. C++/MATLAB 一致性

MATLAB R2024b 24.2.0.2712019 实际执行。72 项检查、0 失败：

- bit/置换索引和 SHA256；
- 置换唯一性、范围和 CC pair；
- BPSK、burst mask、标准高斯样本应用、received、hard、LLR；
- BCH padded/encoded/decoded、syndrome、lookup；
- CC 状态编号、next state、171/133 输出顺序；
- 显式 Viterbi tie-break、tie count、traceback 和 payload。

浮点 channel/LLR 复算均在脚本阈值内，没有 mismatch、NaN 或 Inf。

## 7. Smoke 与预扫描条件

- 固定 channel vector：Es/N0=2 dB，32 symbol，25% MIDDLE，只用于公式验证。
- 参数预扫描：Es/N0={4,8} dB，突发比例={2%,5%,10%}，六位置，每 case 50 帧。
- BCH 10 个候选、CC 7 个候选，共 612 行。
- 72 个同组公平比较组，37 个具有候选 FER 区分度并用于排名；饱和组仍完整保留。
- 同组 frames、payload、noise、burst start、frame sequence hash 完全一致。

## 8. 等跨度方法比较与内部敏感性

等跨度方法组：

- BCH：`FULL_FRAME_285`，比较 CODEBLOCK D=19、ROW_COLUMN 和 GLOBAL_PSEUDORANDOM。
- CC：`TRELLIS_SPAN_32/64/128`，分别比较 SHORT_DEPTH_BLOCK 与 PSEUDORANDOM。

方法内部扫描：BCH CODEBLOCK D=4/8/16/19、ROW_COLUMN rows=4/8/15/19；CC SHORT_DEPTH D=4/8/16、PSEUDORANDOM span=32/64/128。

不把局部 D=4 与全帧伪随机的差异解释为纯方法差异。

## 9. Stage09 候选与排名

评分越低越好，公开权重：平均 FER 0.40、六位置最坏 FER 0.30、bufferFraction 0.15、deinterleave CPU 0.15，并保留 Pareto 标记。

- BCH 综合推荐：BCH_CODEBLOCK D=19。
- CC 综合推荐：PSEUDORANDOM span=128 trellis steps。
- Formal 方法内冻结：BCH NONE=0、CODEBLOCK=19、ROW_COLUMN=15、GLOBAL=285；CC NONE=0、SHORT_DEPTH=8、PSEUDORANDOM=128。

这些仅是 50 帧/case 的筛选结论，不是正式 FER 或突发容限结论。

## 10. Formal 任务规模

- 每编码比较组：31 Es/N0×3 ratio×6 position=558。
- BCH：558×4=2232 方案点。
- CC：558×3=1674 方案点。
- 总方案点：3906；两编码比较组合计 1116。
- 单线程估算：minFrames 约 0.19 小时，按 5000 帧规划约 0.97 小时，maxFrames 上限约 9.70 小时。
- 最大磁盘估算约 770.5 MiB；假设每点 2 KiB 汇总、每 1000 帧 checkpoint 4 KiB，不保存逐帧 trace。
- 估算由预扫描 decode+deinterleave 均值乘 1.5 调度/信道/I/O 系数得到；Formal 前需 Release 小批量校准。

## 11. Checkpoint 恢复方案

每 1000 帧保存 configHash、caseKey、nextFrameIndex、累计计数、计时样本和 frameSequenceHash。恢复前验证配置与 case；从 nextFrameIndex 继续；合并 Gate 验证无重复、无跳帧且序列 hash 一致。真实中断恢复测试必须在 Stage10 功能运行前先通过。

## 12. 高 SNR 零值和资产 Gate

Smoke/Formal 配置均冻结：原始 CSV 保留 0；对数图不画零点；不替换伪小值；不延伸水平线；不显示 error floor 或零错上界标记。零后非零将阻止发布。

所有非 build 新目录具有 readme；Stage09 三轮旧结果均进入版本化 archive；正式每图独立目录、原始数据绝对路径、figure-data、manifest、validation、SHA256 将在 Stage15 强制检查。

## 13. 已知问题与风险

- Prescan 样本量小，只用于筛选。
- CPU 时间依赖当前 Windows/MinGW 平台与系统负载。
- 真实 Formal checkpoint 恢复测试尚未执行。
- 扩展擦除和强干扰未做。
- LDPC N560 历史数据只兼容普通 BPSK+AWGN，不能参与当前突发交织排名，只能进入独立参考表。
- 当前功能内容未 commit，不能生成真实 Git functional range；所有 manifest 均如实保留空 ranges。

## 14. 是否建议进入 Stage10

功能与 Smoke Gate 支持进入 Stage10 前准备，建议在人工确认后先执行 Release 小批量计时校准和 checkpoint 中断恢复测试，再启动 BCH Formal。

当前总状态：PASS_STAGE01_09，Stage10 未启动。

**等待人工确认，尚未启动 Stage10 Formal。**

