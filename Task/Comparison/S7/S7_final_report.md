# S7 交织抗连续突发错误最终报告

## 1. 任务目的

在固定 BCH 低速电文和卷积码高速电文方案下，研究交织方法、跨度、突发比例与位置对 BER、FER、连续突发容限、缓冲和 CPU 开销的影响。主 Formal 信道为 AWGN 下接收机未知的连续 BPSK 极性反转。

## 2. 固定编码方案

- BCH：200 bit payload，补齐为 19×BCH(15,11,1)，发送 285 bit，硬判决后解交织并查表译码。
- 卷积码：300 bit payload，K=7，171/133（八进制），6 个清零尾比特，发送 612 bit；LLR 解交织后使用浮点软判 Viterbi，从状态 0 traceback。
- LDPC：S6 Direct BG2 N560 历史表仅使用普通 BPSK+AWGN，和 S7 突发信道不兼容，只进入独立参考表。

## 3. 信道、随机性和统计

调制为 `0→+1, 1→-1`。突发区间在调制后令 `h[k]=-1`，其他位置 `h[k]=+1`，接收为 `y[k]=h[k]x[k]+n[k]`；接收机不知道区间，突发不绕回。Formal 使用 31 个 Es/N0 点（-5～10 dB，0.5 dB 步长）、2%/5%/10% 和六位置。比较组共享 payload、标准高斯母噪声、突发起点和帧集合。

停止规则为 minFrames=1000、targetFrameErrors=200、maxFrames=50000 的 paired stopping。Stage12 全起点扫描在三个自动工作点、5%/10% 下每起点固定 200 个共享帧。

## 4. 交织方式与比较边界

BCH Formal 比较 NONE、BCH_CODEBLOCK D=19、ROW_COLUMN rows=15 和 GLOBAL_PSEUDORANDOM 285 bit；三种交织方法均属于等跨度 285 的受控比较。

卷积码比较 NONE、SHORT_DEPTH_BLOCK D=8（64 trellis steps）、PSEUDORANDOM span=128 和 SHORT_DEPTH_BLOCK D=16（128 trellis steps）。D8 与 PSEUDO128 只能解释为推荐工程配置对比；D16 与 PSEUDO128 才是等跨度 128 的纯方法受控比较。

## 5. 验证结果

- C++ 单元测试与无噪声回归：PASS。
- MATLAB R2024b 独立参考：72/72 PASS。
- BCH syndrome table：runner 初始化一次并复用，回归 PASS。
- Formal checkpoint 中断恢复：8/8 非计时字段一致，无重复或跳帧。
- BCH Formal：2232 行、558 组，PASS。
- CC Formal：2232 行、558 组，PASS。
- Stage12：BCH 6348 行/1587 组；CC 13608 行/3402 组，PASS。
- 科研图：BCH 29、CC 21，共 50 张，资产与 SHA Gate PASS。BCH 全起点热力图正式展示 2%与5%；10%下所有起点和配置 FER=1 的旧图已归档，原始数据仍保留。

## 6. BCH 结果与推荐

公开权重综合排名第一为 `BCH_ROW_COLUMN_R15`，其全 Formal 平均 FER 为 0.781811；`BCH_CODEBLOCK_D19` 为 0.782191，二者非常接近；全帧伪随机为 0.932620。

在 10 dB、六位置最坏 FER≤0.1 的判据下，ROW_COLUMN R15 与 CODEBLOCK D19 均通过 2% 和 5%，但 10% 最坏 FER 为 1。因此在当前测试网格内，推荐 BCH 行列交织 rows=15，连续突发容限记为 5%；不得外推到 5%～10% 之间的未测比例。

推荐方案的 frames 加权观测为：纯译码约 9053 ns，交织约 328 ns，解交织约 327 ns，附加 CPU 约 655 ns；bufferBits/startupDelayBits 均为 285。CPU 数值只代表当前机器，结构等待量不是物理时间。

## 7. 卷积码结果与推荐

综合排名第一为 `CC_PSEUDO_128_RECOMMENDED`，全 Formal 平均 FER 为 0.906392；D8 为 0.943758，D16 为 0.962055。PSEUDO128 同时属于推荐工程配置组和与 D16 的等跨度 128 受控组。

在 10 dB、六位置最坏 FER≤0.1 的判据下，PSEUDO128 在 2% 的最坏 FER 仍为 0.84，D8 为 0.85，其他配置为 1；所有 CC 配置均标记 `BELOW_MIN_TESTED_2_PERCENT`。因此只能推荐 PSEUDO128 作为当前候选中的相对较优工程配置，不能宣称其在已测网格内满足突发容限目标。

推荐方案的 frames 加权观测为：纯译码约 307559 ns，交织约 751 ns，解交织约 396 ns，附加 CPU 约 1146 ns；bufferBits/startupDelayBits=256，startupDelayTrellisSteps=128。

## 8. 全起点与位置敏感性

Stage12 自动选择 BCH -5/5.5/10 dB 和 CC -5/-3/10 dB。BCH 不同配置在全起点扫描中出现从 FER=0 到 FER=1 的明显位置差异；CC 在 10% 高工作点下四配置所有起点均饱和为 FER=1。逐起点 FER 分辨率为 0.005，适合定位边界和最坏起点，但不替代 Stage10/11 paired Formal。

## 9. FER 改善与 Es/N0 增益

FER 绝对改善、相对降低和改善倍数均使用同 scheme、同 SNR、同比例的 NONE 六位置均值为基线。NONE 基线在目标 FER=0.5 附近没有唯一合法 crossing，因此所有目标 FER Es/N0 gain 均留空并标记不可插值；未平滑曲线或制造增益数字。

## 10. BCH 误纠限制

BCH Formal 记录 `undetectedFrameErrors=5,439,787`、`miscorrectedBlocks=23,251,548`、`detectedFailureFrames=0`。这是完美 Hamming 型 BCH(15,11,1) syndrome 查表在多错误模式下可能映射到错误单比特纠正的固有限制。BCH 性能结论必须与该限制一起使用。

## 11. LDPC 独立参考

独立表保留 BP/NMS 共 62 行：Direct BG2、K=300、N=560、Zc=56、filler=148、parity=112、maxIter=32，NMS alpha=0.95。其信道无连续极性反转、位置扫描或 S7 paired stopping，禁止进入交织收益排名、突发容限和 BCH/CC 统一结论。

## 12. 高 SNR 零值与绘图

Formal 原始 CSV 保留真实零值；本次 BCH/CC Formal 均无 BER/FER 零值行。绘图器仍执行冻结政策：对数图不画零值，不替换伪小值、不延伸水平线、不显示 error floor、零错上界或相应标记；非零异常点不平滑、不删除。

## 13. 推荐结论

- BCH 低速电文：推荐 ROW_COLUMN rows=15；在冻结判据和测试网格内支持 5% 连续极性反转，10% 不支持。
- 卷积码高速电文：相对推荐 PSEUDORANDOM span=128；2% 的最坏位置 FER 仍不满足 0.1，不能声明已达到测试网格内突发容限。
- LDPC：仅保留 AWGN-only 独立历史参考，不参与上述推荐。

## 14. 限制与后续建议

- 擦除和未知连续强干扰扩展未做。
- 推荐依赖公开权重：平均 Formal FER 40%、高工作点最坏起点 FER 30%、buffer 15%、解交织 CPU 15%；应结合分项和 Pareto 标记使用。
- CPU 时间依赖本机和构建环境，缺少符号率时不得换算物理延迟。
- 如需提高 CC 连续极性反转容限，应研究更长跨度、跨帧交织或接收机突发检测；这属于后续任务，不在 S7 当前范围内。
- 当前未 commit、未 push、未合并 `main`。
