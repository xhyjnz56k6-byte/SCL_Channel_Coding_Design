# 一、总体判断

你提出的修改方向大部分是正确的，而且已经从“补几张图”升级为：

> **重新定义 Stage09～Stage15 的职责边界，修复实验逻辑，扩大正式仿真规模，再用统一数据支撑最终方案选型。**

我赞同的核心方向包括：

* Stage10 补齐 R34、增加 FER 层级，并在真滑窗修复后复核 (D_{\mathrm{tb}}=84)；
* 所有阶段旧结果统一归档，禁止覆盖；
* Stage11 补齐位宽和完整 SNR 曲线，重画可读性更高的图；
* Stage13 改成严格控制变量实验，并实现自动选优；
* Stage14 改成真实逐时隙到达驱动译码；
* Stage14 补齐 R34 和 (-5\sim10) dB 大规模仿真；
* Stage15 必须真正集成量化位宽、回溯深度、滑窗、译码时延和 BER/FER，而不是只引用整块基线。

但是，我对部分执行方式有几点重要异议。

---

# 二、我与你存在的主要分歧

## 2.1 不能把所有参数组合都直接跑满正式大规模仿真

例如 Stage13 若直接组合：

* 4 个窗口长度；
* 4 个滑动步长；
* 5 个回溯深度；
* 3 个码率；
* 31 个粗网格 SNR 点；
* 每点最多 50000 帧；

组合数量为：

[
4\times4\times5\times3\times31=7440\text{ 个参数-SNR点}
]

最坏帧数：

[
7440\times50000=3.72\times10^8\text{ 帧}
]

这还没包含 dense 加密、硬判决、量化方案和重复计时。

这不是合理的科研设计，而是无控制地消耗算力。

正确方式必须分成：

```text
单元验证
→ 小规模预扫描
→ 控制变量筛选
→ 候选淘汰
→ 少量候选正式粗网格
→ waterfall加密
→ 最终联合验证
```

---

## 2.2 Stage13 不应该一开始就和完整块画 BER/FER 曲线

你提出：

> 先选择好 W、S、D，再和完整块译码根据 SNR 比较 BER、FER、译码时延和复杂度。

我赞同，而且这是更科学的方式。

Stage13 应分成两个子任务：

### 参数选优阶段

只研究：

* (W) 对性能和时延的影响；
* (S) 对输出节奏和复杂度的影响；
* (D) 对可靠性和回溯代价的影响。

### 最终候选对比阶段

只有自动选出少量候选后，再比较：

```text
完整块 Viterbi
连续有限回溯 Viterbi
真滑窗 Viterbi
```

这部分可以仍放在 Stage13 的正式结果中，也可以由 Stage15 汇总。

我的建议是：

* Stage13 输出“算法级正式对比”；
* Stage15 输出“系统级最终对比”。

---

## 2.3 Stage14 的 slot 长度不一定导致 BER/FER 差异

即使修复成真实逐 slot 到达：

* 编码状态连续；
* 打孔相位连续；
* 中间不加尾比特；
* 最终码流相同；
* 最终接收符号相同；

那么 `50×6`、`100×3`、`150×2` 的最终 BER/FER 仍可能非常接近，甚至完全相同。

真实逐 slot 到达主要改变的是：

* 窗口触发时刻；
* 首次输出时延；
* 平均决策时延；
* 缓存峰值；
* 输出批次；
* 调度次数；
* CPU开销；
* 边界附近的输出行为。

所以 Stage14 修复后，不能预设：

> 三种时隙组织的 BER/FER 一定会明显分开。

如果仍然重合，这是可能且合理的结论。

---

## 2.4 Stage15 不应该把所有参数全部塞到一张图中

Stage15 必须包含量化位宽、回溯深度和译码时延，但不能把几十条曲线全部堆到一张 BER/FER 图里。

更合理的是分层汇总：

1. 最终候选 BER/FER；
2. 量化位宽性能损失；
3. 回溯深度性能—内存权衡；
4. 滑窗参数时延—可靠性权衡；
5. 最终系统方案 Pareto 图。

否则图例会再次失控。

---

# 三、统一的旧结果归档规范

你的归档要求非常合理，应提升为所有 Stage 的硬性规则。

## 3.1 目录结构

每个阶段统一：

```text
stageXX_name/
├─ results/
│  ├─ 当前最新结果
│  └─ 当前最新图
├─ archive/
│  ├─ v01_20260729_before_xxx/
│  ├─ v02_20260730_before_xxx/
│  └─ ...
├─ readme.txt
├─ validation_report.md
└─ manifest.json
```

## 3.2 命名规则

格式：

```text
v版本号_日期_before_本轮修改内容
```

例如：

```text
v01_20260729_before_r34_traceback_extension
v02_20260730_before_quantization_full_grid
v03_20260731_before_true_window_scheduler
```

要求：

* 全英文；
* 全小写；
* 下划线分隔；
* 不使用空格；
* 不使用中文；
* 不覆盖旧 archive；
* 每轮版本号递增。

## 3.3 归档内容

归档的不只是 PNG，还包括：

```text
原始CSV
figure-data CSV
PNG
plot manifest
validation report
known issues
运行命令
参数文件
结果哈希
```

## 3.4 归档顺序

每次修改前执行：

```text
1. 检查 results/ 当前内容
2. 创建新的 archive/vXX_日期_before_修改名/
3. 将上一轮 results/ 内容完整移动进去
4. 写 archive_manifest.json
5. 再运行本轮实验
6. 新结果只写入 results/
```

禁止：

* 直接删除旧文件；
* 新旧 CSV 混在同一 results；
* 用同名覆盖但不归档；
* 只归档图片、不归档数据。

---

# 四、Stage09 修改规划

Stage09 是整个后续工作的统一 AWGN 基线，必须稳定，不宜频繁扩展职责。

## 4.1 保留两层网格

### 粗网格

```text
SNR = Es/N0
范围：-5～10 dB
步长：0.5 dB
31点/Case
```

停止条件：

```text
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
```

### dense 网格

围绕每条曲线的 waterfall 区域：

```text
优先0.1 dB
算力不足时0.2 dB
```

## 4.2 正式 Case

```text
R12-hard
R12-soft-float
R23-hard
R23-soft-float
R34-hard
R34-soft-float
```

## 4.3 Stage09 只负责

* 完整块；
* 硬/浮点软判决；
* 三个码率；
* BER/FER；
* 基准吞吐；
* 基准时延。

Stage09 不负责：

* Q3～Q8；
* Dtb；
* 滑窗；
* 时隙组织。

---

# 五、Stage10 正式修改规划

## 5.1 目标重新定义

Stage10 要回答：

> 对 R12、R23、R34，有限回溯深度需要多大，才能接近完整块译码，同时减少 survivor 内存和输出等待？

---

## 5.2 参数范围

至少：

```text
Dtb = 35, 49, 70, 84, 98, 112
```

完整块参考：

```text
BLOCK_FULL_TRACEBACK
```

R34 至少正式测试：

```text
70, 84, 98, 112
```

为了统一绘图，建议 R34 也运行全部六个 Dtb。

---

## 5.3 每个码率选择三个 FER 层级

目标层级：

```text
FER ≈ 0.30
FER ≈ 0.10
FER ≈ 0.03
```

选择方式不能手工随意指定，应从 Stage09 dense 曲线自动查找最接近目标 FER 的 SNR。

例如输出：

```text
stage10_selected_snr_by_fer_level.csv
```

字段：

```text
rateCase
targetFer
selectedSnrDb
observedFer
sourceCsv
sourceRow
selectionError
```

---

## 5.4 仿真规模

每个 Dtb、码率、FER层级：

```text
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
```

同一场景下所有 Dtb 共用 payload 和母噪声。

---

## 5.5 Stage10 新增指标

```text
BER
FER
BER/FER 95% CI
relativeBerIncreaseVsBlock
relativeFerIncreaseVsBlock
decodedBitMismatchVsBlock
decodedFrameMismatchVsBlock
survivorMemoryBytes
pathMetricMemoryBytes
tracebackOperations
ACSCount
firstDecisionDelaySymbols
avgDecisionDelaySymbols
avgDecodeTimeUs
p95DecodeTimeUs
```

---

## 5.6 重新验证 Dtb=84

这部分必须分两步。

### 第一步：独立有限回溯验证

仍在 Stage10 中完成：

```text
Dtb=84 vs 完整块
```

### 第二步：真滑窗修复后复核

Stage13 自动选出的真滑窗中，固定或包含：

```text
D=84
```

比较：

```text
真滑窗 D84
连续有限回溯 D84
完整块
```

检查 D84 是否在窗口化调度下仍然满足性能门限。

---

## 5.7 Stage10 绘图

建议保留 4 张主图，并增加 2 张附图。

### 主图

1. `Dtb—BER`
2. `Dtb—FER`
3. `Dtb—CPU译码时间`
4. `Dtb—survivor内存`

### 新增附图

5. `Dtb—相对完整块FER增幅`
6. `内存—可靠性权衡`

完整块不能再和有限 Dtb 时延折线直接相连，应单独显示为参考点或虚线。

---

# 六、Stage11 正式修改规划

## 6.1 目标重新定义

Stage11 要回答：

> 软信息使用多少位量化，可以在接近 Float 性能的同时降低输入存储、运算和硬件资源？

---

## 6.2 正式位宽

必须覆盖：

```text
Q3
Q4
Q5
Q6
Q7
Q8
Float
```

禁止再把 Float 画成横轴 64。

绘图横轴使用分类：

```text
Q3, Q4, Q5, Q6, Q7, Q8, Float
```

---

## 6.3 码率范围

必须覆盖：

```text
R12
R23
R34
```

---

## 6.4 完整 SNR 曲线

每个位宽、码率运行：

```text
-5～10 dB
步长0.5 dB
```

停止条件：

```text
minFrames=1000
targetFrameErrors=200
maxFrames=50000
```

对最终候选 Q5、Q6、Q7、Q8 和 Float，在 waterfall 区域进行 0.1 dB 加密。

不建议给所有位宽都做完整 dense，否则计算量太大。

---

## 6.5 clipMax 的处理

先做小规模预扫描：

```text
clipMax = 1.5, 2.0, 2.5, 3.0, 4.0
```

每个位宽可以选自己的推荐 clip，但必须另外提供一个统一 clip 对比，避免过度调参。

推荐输出：

```text
bestClipPerQuantMode
globalBalancedClip
```

---

## 6.6 saturation 定义必须先审查

必须明确区分：

```text
trueClipCount：
原始值超出[-clipMax, clipMax]

edgeBinCount：
量化后落在最外层量化级

integerOverflowCount：
整数表示溢出

pathMetricSaturationCount：
路径度量饱和
```

之前的 saturationCount 很可能混合了“越界裁剪”和“边缘量化级”。

正式图只画：

[
\text{clipRate}
===============

\frac{\text{trueClipCount}}
{\text{totalQuantizedSamples}}\times100%
]

---

## 6.7 Stage11 重新绘图

### BER 图

建议不要做一个大图，而是：

```text
stage11_r12_quantization_ber.png
stage11_r23_quantization_ber.png
stage11_r34_quantization_ber.png
```

每张图：

* 横轴：SNR；
* 纵轴：BER；
* 曲线：Q3～Q8、Float。

为了避免 7 条曲线过密，可以分成：

```text
low_precision：Q3,Q4,Q5
high_precision：Q6,Q7,Q8,Float
```

### FER 图

同样按码率拆分。

### 固定代表 SNR 分类图

每个场景单独画：

```text
横轴：Q3～Q8、Float
纵轴：BER或FER
```

### 时延图

分组柱状图：

```text
横轴：量化模式
柱组：R12、R23、R34
纵轴：平均/P95译码时间
```

### 存储图

```text
横轴：R12、R23、R34
每组：Q3～Q8、Float
纵轴：输入存储KB
```

### 饱和图

```text
横轴：量化模式
纵轴：真实裁剪比例(%)
```

### 性能损失图

正式必须增加：

```text
横轴：量化模式
纵轴：相对Float的SNR损失(dB)
```

目标：

```text
FER=10^-1
FER=10^-2
```

若未覆盖，写 `N/A`，不得外推。

---

# 七、Stage13 真滑窗正式重构规划

## 7.1 第一件事：先修算法，而不是先重跑

必须证明：

* survivor 实际只保存 (W) 范围；
* 使用环形缓存或窗口局部缓存；
* W 控制缓存大小；
* S 控制窗口推进；
* D 控制回溯；
* final flush 不依赖完整 306 时刻历史；
* 窗口起点状态度量明确传递；
* 无丢 bit、无重复 bit；
* 每个 bit 恰好输出一次。

约束：

[
W>D
]

建议进一步要求：

[
S\le W-D
]

---

## 7.2 三组严格控制变量实验

### 实验 A：窗口长度

固定：

```text
D=70
S=16
```

变化：

```text
W=96,128,160,192
```

回答：

* W 增大对 BER/FER 的影响；
* 首次输出是否增加；
* 内存是否线性增加；
* mismatch 是否下降。

### 实验 B：滑动步长

固定：

```text
W=128
D=70
```

变化：

```text
S=8,16,25,50
```

回答：

* 输出批次频率；
* 稳态输出间隔；
* ACS和回溯次数；
* CPU处理量；
* BER/FER是否变化。

### 实验 C：回溯深度

固定：

```text
W=128
S=25
```

变化：

```text
D=35,49,70,84,98
```

回答：

* D 对性能；
* D 对等待；
* D 对内存和回溯操作；
* D84是否仍然合理。

---

## 7.3 Stage13 仿真规模分级

### 预扫描

每个配置：

```text
1000帧
3个代表SNR
```

淘汰：

* 无噪声 mismatch；
* 丢 bit；
* 重复 bit；
* FER损失过大；
* 内存过大；
* 不满足合法性约束。

### 正式候选

每个码率保留 2～4 个候选。

再运行：

```text
-5～10 dB
0.5 dB
minFrames=1000
targetErrors=200
maxFrames=50000
```

### dense

每个码率最终保留 1～2 个候选，waterfall 0.1 dB 加密。

---

## 7.4 自动选优设计

自动选优不能再硬编码 `W96/S25/D70`。

建议采用“硬门限 + Pareto 排序”。

### 第一层：正确性硬门限

必须满足：

```text
noiselessMismatch = 0
lostBits = 0
duplicateBits = 0
outputLength = 300
finalFlushPass = true
```

### 第二层：可靠性门限

相对完整块：

```text
FER relative increase <= 5%
或
SNR loss at FER=0.1 <= 0.1 dB
```

建议两个条件都记录，不强制同时满足。

### 第三层：资源与时延评分

归一化指标：

```text
firstOutputDelay
p95DecisionDelay
windowMemory
survivorMemory
ACSCount
tracebackOperations
processingTime
```

### 第四层：输出多个推荐

```text
performance_first
latency_first
memory_first
complexity_first
balanced
```

balanced 可以采用加权评分，但权重必须写入 manifest，例如：

[
Score=
0.35L_{\mathrm{FER}}
+0.20L_{\mathrm{delay}}
+0.20L_{\mathrm{memory}}
+0.15L_{\mathrm{operations}}
+0.10L_{\mathrm{cpu}}
]

权重不是唯一真理，所以必须同时保留 Pareto 前沿，避免只依赖主观权重。

---

## 7.5 Stage13 与完整块如何比较

你的理解是正确的。

正确顺序：

```text
先完成W/S/D控制变量研究
→ 自动筛选候选
→ 再做完整块、有限回溯、真滑窗对比
```

正式对比对象：

```text
Block full traceback
Continuous truncated D84
Sliding-window performance-first
Sliding-window balanced
Sliding-window latency-first
```

比较图：

1. BER-SNR；
2. FER-SNR；
3. 首次输出时延；
4. 平均/P95决策时延；
5. CPU处理时间；
6. 实际内存；
7. ACS/回溯操作数；
8. FER—时延 Pareto；
9. FER—内存 Pareto。

这部分建议 Stage13 生成正式图，Stage15只选代表方案汇总。

---

# 八、Stage14 正式重构规划

## 8.1 真实逐 slot 到达

必须把当前：

```text
各slot编码
→ 拼接完整rx
→ 一次性decode
```

改成：

```text
slot1编码符号到达
→ 加入接收缓存
→ 触发可执行窗口
→ 记录输出事件

slot2到达
→ 继续更新
→ 继续输出
...
```

每一个接收符号都要有：

```text
arrivalSymbolIndex
```

每一个 payload bit 要记录：

```text
decisionSymbolIndex
```

决策时延：

[
delay_i=
decisionSymbolIndex_i-arrivalSymbolIndex_i
]

不能再用信息 bit 序号和编码符号序号直接相减。

---

## 8.2 正式方案

```text
A_BLOCK_300
B_CONT_50x6
C_CONT_100x3
D_CONT_150x2
```

码率：

```text
R12
R23
R34
```

---

## 8.3 正式 SNR 网格

你要求：

```text
-5～10 dB
步长0.5 dB
```

停止条件：

```text
minFrames=1000
targetFrameErrors=200
maxFrames=50000
```

我同意。

waterfall dense 建议只对：

* 每个码率的 Block；
* 每个码率的最终连续候选；

进行 0.1 dB 加密，不必对 12 个方案全部 dense。

---

## 8.4 Stage14 应统计的时序指标

```text
firstOutputDelaySymbols
avgDecisionDelaySymbols
medianDecisionDelaySymbols
p95DecisionDelaySymbols
maxDecisionDelaySymbols
fullFrameLastDecisionSymbol
steadyOutputIntervalMean
steadyOutputIntervalP95
outputBatchCount
slotTriggerCount
windowTriggerCount
peakRxBufferSymbols
avgRxBufferSymbols
processingTimeUs
```

---

## 8.5 边界 BER

边界相对位置：

```text
offset=-10...+9
```

统计：

```text
BER(offset)
```

同时输出：

```text
boundaryBER
nonBoundaryBER
boundaryToNonBoundaryRatio
```

必须附置信区间。

---

## 8.6 Stage14 六张正式图

1. 四种组织方式 BER-SNR 曲线；
2. 四种组织方式 FER-SNR 曲线；
3. 边界相对位置 BER；
4. 首次输出时延柱状图；
5. 平均/P95/完整帧时延对比；
6. 归一化有效吞吐-SNR 曲线。

建议每个码率单独一套，避免 12 条曲线堆在一张图中。

另外生成一张码率汇总图，只放每个码率的最终代表方案。

---

# 九、Stage15 最终集成规划

Stage15 必须重新定义为：

> **只使用经过正式大规模仿真的最终候选，不引用预扫描点作为最终结论。**

---

## 9.1 最终候选必须包含

### 判决方式

```text
Hard
Soft Float
Soft Quantized Final
```

### 量化

至少包含最终选出的：

```text
Qbalanced
Float
```

例如最终可能是 Q6 或 Q7，但不能预先写死。

### 回溯

```text
Full traceback
D84
Stage10 final balanced D
```

如果 D84 与最终 balanced 相同，可合并。

### 调度

```text
Block
Continuous truncated
True sliding-window
```

### 组织方式

```text
Block300
50x6
100x3
150x2
```

但只选 Stage14 中经过正式筛选的代表方案进入最终主图。

---

## 9.2 Stage15 必须使用相同 SNR 网格

所有最终候选至少都要有：

```text
-5～10 dB
0.5 dB
```

并对关键曲线做 dense 加密。

不能再出现：

```text
R12只用0 dB
R23只用1 dB
```

却放在同一张最终权衡图中的问题。

---

## 9.3 Stage15 最终必需图

你要求必须输出：

> 对比 BER/FER、度量量化位宽、回溯深度和译码时延。

我建议至少生成以下 8 张最终图。

### 图1：最终候选 BER-SNR

只放最终代表方案。

### 图2：最终候选 FER-SNR

只放最终代表方案。

### 图3：量化位宽性能损失

```text
横轴：Q3～Q8、Float
纵轴：相对Float的SNR损失(dB)
```

### 图4：回溯深度性能—内存权衡

```text
横轴：survivor memory
纵轴：相对完整块FER增幅
```

### 图5：最终方案首次输出时延

```text
横轴：最终方案
纵轴：首次输出等待（符号）
```

### 图6：最终方案CPU译码时间

```text
横轴：最终方案
纵轴：平均/P95译码时间（μs）
```

### 图7：最终方案吞吐—FER Pareto

必须在相同 SNR 下比较。

### 图8：最终方案时延—可靠性 Pareto

```text
横轴：首次输出或P95决策时延
纵轴：目标FER所需SNR
气泡大小：总内存
```

---

## 9.4 Stage15 最终表格

必须输出统一总表：

```text
stage15_final_scheme_matrix.csv
```

字段至少包括：

```text
schemeId
rate
decisionMode
quantMode
quantBits
clipMax
tracebackMode
dtb
window
slide
organization
snrDb
BER
FER
berCiLow
berCiHigh
ferCiLow
ferCiHigh
normalizedGoodput
firstOutputDelaySymbols
avgDecisionDelaySymbols
p95DecisionDelaySymbols
fullFrameDelaySymbols
avgDecodeTimeUs
p95DecodeTimeUs
inputMemoryBytes
survivorMemoryBytes
pathMetricMemoryBytes
totalMemoryBytes
ACSCount
tracebackOperations
```

---

# 十、统一绘图规则补充

所有 Stage10～15 新图：

* 不能使用过载图例；
* 每张主图建议不超过 6～8 条曲线；
* 三个码率必要时拆成三张；
* 参数名称写成：

  * `R23-W128-S25-D84`
  * 不再写难懂的 `CC-C-R23-S-25-84`；
* Float 使用分类标签；
* 不把 Float 当作 64-bit 定点；
* 零错误点使用空心标记或上界箭头；
* 置信区间可以用误差条或阴影；
* 折线只连接“仅一个自变量变化”的点；
* 多参数候选使用散点图，不强行连线。

---

# 十一、建议的执行顺序

## 阶段 1：归档与状态修正

1. 为 Stage09～15 当前结果建立 archive；
2. 生成 archive manifest；
3. 将 Stage13、14、15 状态改为 `BLOCKED`；
4. 将 Stage10、11 改为 `PARTIAL_PASS`。

## 阶段 2：修复算法基础

5. 修复 Stage13 真窗口缓存和 final flush；
6. 修复 Stage14 逐 slot 到达；
7. 增加时间戳、输出事件、缓冲统计。

## 阶段 3：补齐 Stage10

8. R12/R23/R34；
9. 三个 FER 层级；
10. 六个 Dtb；
11. 正式样本和置信区间；
12. 输出 Dtb 初步推荐。

## 阶段 4：补齐 Stage11

13. Q3～Q8、Float；
14. R12/R23/R34；
15. 完整粗网格；
16. 关键候选 dense；
17. clip 定义和饱和比例；
18. 重画全部图。

## 阶段 5：重做 Stage13

19. 三组控制变量实验；
20. 自动选优；
21. 候选正式粗网格；
22. dense；
23. 与完整块、连续回溯正式对比；
24. 复核 D84。

## 阶段 6：重做 Stage14

25. 三个码率；
26. 四种组织方式；
27. (-5\sim10) dB；
28. 真实 slot 到达；
29. 边界 BER；
30. 时延、缓存、吞吐正式输出。

## 阶段 7：重做 Stage15

31. 只读取正式通过结果；
32. 生成统一 scheme matrix；
33. 输出最终 8 张图；
34. 重新回答 5 个核心问题；
35. 形成五类推荐；
36. 最后重新判定总 Gate。

---

# 十二、最终 Gate 建议

只有满足以下条件才能输出：

```text
PASS_CC_S3_INTEGRATION
```

## Stage10

* R12/R23/R34；
* 3 个 FER 层级；
* 正式统计；
* D84复核。

## Stage11

* Q3～Q8、Float；
* R12/R23/R34；
* 完整曲线；
* 性能损失 dB；
* clip 定义正确。

## Stage13

* 真窗口缓存；
* 真窗口推进；
* 自动选优；
* 完整 SNR 正式候选；
* 与完整块对比。

## Stage14

* 真 slot 到达；
* R12/R23/R34；
* 完整粗网格；
* 边界和时延定义正确。

## Stage15

* 所有最终方案同 SNR 比较；
* BER/FER；
* 量化位宽；
* 回溯深度；
* 译码时延；
* 内存；
* 吞吐；
* 最终推荐全部有正式大规模数据支撑。

---

# 十三、最后的正式判断

你的修改要求总体是合理的，而且应当执行。最重要的三条是：

```text
第一，Stage13、Stage14必须先修算法，再扩大仿真；
第二，Stage15必须只使用正式大规模结果，不能用零散预扫描点；
第三，参数研究必须先控制变量和筛选，再做最终联合比较。
```

我唯一明确反对的是：

> 对所有参数组合直接做全范围、全帧数穷举。

这既浪费算力，也会使结果难以解释。

合理方案应是：

```text
控制变量预扫
→ 自动筛选
→ 少量候选正式粗网格
→ waterfall加密
→ Stage15联合验证
```

这样才能同时保证实验规模、科学性、可解释性和可执行性。
