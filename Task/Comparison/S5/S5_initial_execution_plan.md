# S5 高速电文不同信道对比仿真：初始执行规划

> 文档状态：`PLAN_READY_FOR_REVIEW` 前的规格冻结稿  
> 本轮性质：S5 第 1 次执行，只做工程审计、历史成果盘点与后续 Stage 规划  
> 生成日期：2026-07-31  
> 正式位置：`Task/Comparison/S5/S5_initial_execution_plan.md`  
> 本轮禁止：编译、测试、Smoke、Formal、实验数据、绘图、commit、push、merge

## 1. 项目与 Git 当前状态

### 1.1 修改前检查

| 项目 | 审计结果 |
|---|---|
| 仓库根目录 | `C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design` |
| 当前分支 | `S5-Compare` |
| 是否在 `main` | 否 |
| 当前 HEAD | `ef56314e06cf2169744ee33b56ad2aea6d9815ca` |
| `main` | `ef56314e06cf2169744ee33b56ad2aea6d9815ca` |
| `origin/main` | `ef56314e06cf2169744ee33b56ad2aea6d9815ca` |
| 当前分支上游 | `origin/S5-Compare` |
| 最新提交 | `ef56314e S5任务规划` |
| 工作区 | 已跟踪文件无修改；未跟踪文件 0 个 |
| 远程 | `origin = https://github.com/xhyjnz56k6-byte/SCL_Channel_Coding_Design.git` |
| 本轮 commit/push | 不执行 |

实际核对的只读命令包括：

```text
git branch --show-current
git status
git log -1 --oneline
git remote -v
git rev-parse HEAD
git rev-parse main
git rev-parse origin/main
git branch --all
git worktree list --porcelain
git merge-base --is-ancestor <CC/LDPC commit> main
git ls-files --others --exclude-standard
```

### 1.2 分支、worktree 与合并状态

1. 本地 `main` 与 `origin/main` 完全一致。
2. CC 工作树提交 `0b6829460bfe099960fb27d0fd851747ab6b2e14` 是 `main` 的祖先。
3. LDPC 工作树提交 `94b098f57eeadeba66ccd5ed007a97c7c8c90a53` 是 `main` 的祖先。
4. `origin/stage01-15-cc-s3-full` 和 `origin/stage01-ldpc` 也均已进入 `main`。
5. `main` 中存在合并提交 `28da96c9 Merge branch 'stage01-cc'` 和 `5796becd Merge branch 'stage01-ldpc'`。
6. 当前共发现 9 个 worktree，包括 CC、LDPC、BCH 多径、CFO/遮挡、突发交织和集成历史工作树。它们仍保留不等于功能未合并；不得在 S5 中删除或清理。
7. `origin/HEAD` 仍指向 `origin/stage01-common-definition`，不是 `origin/main`。这不影响本轮，但属于远程默认分支配置风险。
8. 当前分支名 `S5-Compare` 不符合根规则推荐的 `stageXX-short-description`。本分支由用户明确创建，可承载本轮唯一规划文件；进入功能实现前必须由用户确认它是否作为 S5 批次分支继续使用。

### 1.3 既有 S5 规划

`ef56314e` 已增加 `初始规划/S5-任务规划-v1.md`，共 2853 行。该文件是历史讨论与建议汇总，包含旧的独立 Prescan 设计和未完全冻结的 CC 代表方案。本文件不覆盖它，而是在真实代码、冻结配置和结果审计后形成正式执行规划。

## 2. 审计材料与证据边界

已读取并交叉核对：

- `任务要求/附件3-信道编码、交织与译码方案及仿真分析.pdf`，7 页；
- 同名 `.docx` 的正文和 17 张表；
- `任务要求/信道编码仿真项目参数与实施计划.md`；
- `项目跟进/项目记录.md`；
- `项目跟进/卷积码-S3.md`；
- `项目跟进/LDPC码-S4.md`；
- `初始规划/CODEX_GIT_WORKFLOW.md`；
- `初始规划/S5-任务规划-v1.md`；
- `Task/Common` 的定义、配置、接口、源文件和 Stage 审计记录；
- `Task/CC` 的 Stage01、06、09、13、15 冻结配置、结果和最终推荐；
- `Task/LDPC` 的当前 Direct BG2/NMS 源码、S4 冻结记录和 Stage20/23 验证报告；
- `Task/BCH/simulation/stages/S2` 的多径、CFO、遮挡、突发模型、配置、MATLAB 参考和验证报告；
- `Task/BCH/simulation/current` 的 AWGN、多径和 MMSE 实现。

本轮没有执行任何历史 checker。本文中的 `PASS` 只引用现有报告，不宣称本轮重新验证通过。

## 3. 老师原始任务与 S5 的对应关系

老师原始任务规定：

- 高速电文只保留约 300 bit；
- 高速电文比较卷积码和 5G NR LDPC；
- 卷积码允许整块或按时隙组织，并支持滑窗 Viterbi；
- LDPC 采用 300 bit 整块短码适配，不分块；
- LDPC 不配置交织；
- S5 覆盖 AWGN、多径、频偏、多普勒、短时遮挡、突发错误；
- 输出 BER、FER、译码成功率、译码时延和鲁棒性；
- 交织改善属于独立测试项。

因此 S5 的最终研究问题冻结为：

> 在相同 300 bit payload、相近实际发送长度、统一 Es/N0、公共帧、公共标准高斯噪声、统一信道状态和明确接收机假设下，卷积码与 Direct BG2 QC-LDPC 在六类信道中的可靠性、时延、译码稳定性和相对 AWGN 退化有何差异，并应如何按业务场景选择方案？

## 4. S5 与 S3、S4、S6、S7 的边界

| 任务 | 负责内容 | S5 处理方式 |
|---|---|---|
| S3 | 卷积码码率、硬/软判决、量化、有限回溯、真滑窗、组织方式 | 只选代表方案，不重新优化 |
| S4 | Direct LDPC 码长、BP/NMS、alpha、迭代与复杂度 | 只选 N480/N640 NMS，不重扫 |
| S5 | CC 与 LDPC 在六类信道中的对比 | 本任务 |
| S6 | 不同译码算法专门比较 | 不在六信道重复 Hard/Soft、BP/NMS 全排列 |
| S7 | 交织抗突发错误改善 | S5 只做无交织基线 |

明确非目标：

- 不重新实现 S3 或 S4；
- 不扫描全部 CC 码率、回溯深度、量化位宽和滑窗组合；
- 不扫描全部 LDPC 码长或 alpha；
- 不比较 BP 与 NMS 全曲线；
- 不给 LDPC 加交织；
- 不把 BCH 纳入高速电文性能排名；
- 不引入 Jakes、多径瑞利衰落、分数延时、同步环、多天线或波形过采样。

## 5. 已完成且可复用的模块

### 5.1 Common

| 能力 | 位置 | 审计结论 |
|---|---|---|
| 300 bit 公共帧池 | `Task/Common/include/common/frame_pool.hpp` | 50000 帧、packed bits、SHA256、随机访问 |
| 标准高斯生成 | `gaussian_noise.hpp/.cpp` | `NoiseKey(masterSeed, noiseGroupId, frameIndex, policyVersion)` |
| 噪声池 | `noise_pool.hpp/.cpp` | float64、小端、frame-major、分片 hash |
| BPSK | `modulation.cpp` | `0 -> +1, 1 -> -1` |
| AWGN | `awgn_channel.cpp` | 现接口以 Eb/N0 和实际码率计算 sigma |
| LLR/硬判决 | `demodulation.cpp` | `LLR=2y/sigma^2`，正值表示 bit 0 |
| 指标与停止 | `simulation_metrics.cpp`、`simulation_control.cpp` | BER/FER、时延、停止条件 |
| checkpoint/resume | `checkpoint.cpp` | 配置、帧池、噪声池、SNR、frameIndex 兼容检查 |
| 结果格式 | `result_schema.*` | CSV/JSON 基础字段 |

### 5.2 CC S3

- K=7，memory=6，64 状态；
- 生成多项式 171/133（八进制）；
- 300 bit payload，6 个清零尾比特；
- R1/2：母码和发送长度 612，实际码率 `300/612=0.49019607843137253`；
- R2/3：发送长度 459，实际码率 `300/459=0.6535947712418301`；
- Soft Float、Q3～Q8、完整块、有限回溯和真滑窗均已有实现与历史结果；
- MATLAB `poly2trellis/convenc/vitdec` 已有 0 bit mismatch 的历史 Gate。

### 5.3 LDPC S4

- 自定义 Direct BG2 切割结构，不是 MATLAB 官方 NR rateMatch 链路；
- Direct 编码、Layered BP、Layered NMS、syndrome 提前停止已有实现；
- 最大迭代次数 32；
- Stage23 最终集成 Gate 已记录 PASS；
- 当前信道 LLR 使用 Es/N0：`sigmaSquared=1/(2*10^(EsN0Db/10))`。

### 5.4 BCH S2 可复用的信道证据

- 固定三径 `[1, 0.65, 0.35]`，delay `[0,1,3]`，单位能量归一化；
- 已知信道线性 MMSE，normal equations + banded Cholesky；
- CFO 首相位 0°、末符号累计 30°、不估计、不补偿；
- 遮挡为调制符号域矩形连续全置零，AWGN 保留，随机不回绕起点；
- 突发历史 Formal 是 `FLIP_CONTIGUOUS_BITS`，无 AWGN；该模型不适合直接复用于 CC/LDPC 软信息主链路；
- BCH S2 没有独立多普勒 Stage，不能声称已有冻结参数。

## 6. 禁止重复实现的模块

- CC 编码器、打孔器、完整块/滑窗 Viterbi；
- Direct LDPC 编码器、矩阵构造、Layered NMS；
- Common 帧池、hash、随机种子、BER/FER、checkpoint 基础逻辑；
- BCH S2 已验证的三径卷积和 MMSE 数学逻辑；
- 六套重复 runner。

S5 只允许增加复基带前端、六类单一职责信道模块、统一接收前端、S5 runner/配置/验证和审计层。

## 7. 两组公平比较 Case 与真实参数

### 7.1 主比较矩阵

| 组 | Case | Kpayload | Ntx | actualRate | 译码 |
|---|---|---:|---:|---:|---|
| 高码率 | `CC_R23_BLOCK_FLOAT` | 300 | 459 | 0.6535947712418301 | 完整块 Soft Float Viterbi |
| 高码率 | `LDPC_N480_NMS` | 300 | 480 | 0.625 | Layered NMS，alpha=0.95，maxIter=32 |
| 可靠性 | `CC_R12_BLOCK_FLOAT` | 300 | 612 | 0.49019607843137253 | 完整块 Soft Float Viterbi |
| 可靠性 | `LDPC_N640_NMS` | 300 | 640 | 0.46875 | Layered NMS，alpha=0.80，maxIter=32 |

发送长度差：

- 高码率组：21 symbol，LDPC 比 CC 长 4.575%；
- 可靠性组：28 symbol，LDPC 比 CC 长 4.575%。

### 7.2 为什么主比较使用完整块 Float

S3 没有一个适用于所有业务的唯一最终推荐：

- 可靠性优先：R12 完整块 Float；
- 时延优先：R23 真滑窗，W=128、S=25、D=84；
- 平衡/内存：R12 真滑窗，W=96、S=16、D=70；
- 吞吐优先：R34 真滑窗，不属于本次相近发送长度组。

为使 S5 的主要变量保持为“编码结构 + 信道”，主 Formal 默认使用已验证的完整块 Float R12/R23。真滑窗工程方案只允许作为最终报告的历史 S3 时延背景，不进入六信道 Formal。若用户明确要求代表工程在线接收，则 Stage01 可把 CC 两个 Case 改为上述真滑窗参数，但必须重写公平性说明并保留修改记录。

### 7.3 LDPC 精确冻结参数

| Case | Zc | filler | rankHp | NMS alpha | early stop |
|---|---:|---:|---:|---:|---|
| N480 | 48 | 84 | 96 | 0.95 | 每完整迭代后检查 syndrome |
| N640 | 40 | 20 | 320 | 0.80 | 每完整迭代后检查 syndrome |

N560（Zc=56、filler=148、rankHp=112、alpha=0.95）只记录为扩展候选。它没有体现相对 N480 的可靠性收益，默认不进入六信道 Formal。

## 8. 统一 Es/N0、码率和噪声定义

所有性能曲线横轴：

```text
Es/N0 (dB)
中文：符号信噪比
```

不得写成“比特信噪比 Es/N0”。

公式：

```text
gammaS = 10^(esN0Db/10)
sigmaSquared = 1/(2*gammaS)
sigma = sqrt(sigmaSquared)
actualRate = Kpayload/Ntx
ebN0Db = esN0Db - 10*log10(actualRate)
```

审计发现：

1. CC S3 和 LDPC S4 的实际代码使用上述 Es/N0 sigma 公式。
2. Common 当前公开 `computeAwgnSigma()` 是 Eb/N0 API，内部包含 actualRate。
3. `项目跟进/LDPC码-S4.md` 一处公式写成 `Eb/N0=Es/N0+10log10(R)`，但 S4 代码实际使用减号。该文档公式是历史记录错误，S5 不得复制。
4. S5 必须提供名称明确的 Es/N0 API，禁止把 Es/N0 数值传给旧 Eb/N0 API。

每条结果必须保存：

```text
esN0Db, ebN0Db, actualRate, sigmaSquared, Kpayload, Ntx
```

## 9. 复基带升级方案

### 9.1 数据类型与处理顺序

```text
payload
-> CC/LDPC encode
-> complex BPSK {+1+j0,-1+j0}
-> selected deterministic/random impairment
-> complex AWGN
-> channel-specific equalization/projection
-> soft metric/LLR
-> Viterbi/NMS
-> 300 bit payload metrics
```

计划函数：

```cpp
complexBpskModulate()
applyComplexAwgn()
applyFixedMultipath()
applyCarrierFrequencyOffset()
applyLinearDoppler()
applyShortBlockage()
applyBurstInterference()
equalizeKnownMultipathMmse()
projectOriginalBpskAxis()
computeAwgnLlr()
computeMultipathApproximateLlr()
hardDecisionFromLlr()
```

每个函数只完成一个步骤；信道损伤、AWGN、补偿、LLR、译码互相分离。

### 9.2 公共复噪声策略

候选版本：

```text
complexNoisePolicyVersion = s5_complex_pair_v1
zI[i] = motherNoise[2*i]
zQ[i] = motherNoise[2*i+1]
```

Common 当前 `motherNoiseLength/maxSymbolsPerFrame=1000`。N640 需要 `2*Ntx=1280` 个实样本，因此现有池不足。Stage02 必须：

- 保持 Common-04 policy v1 不变；
- 新增 S5 policy v1，`realSamplesPerFrame=2000`，覆盖最大码块 1000 个复符号；
- 固定 `noisePoolId/noisePoolOverallHash`；
- 拒绝用重复 I 样本构造 Q；
- 不提交 50000 帧的大噪声池。

## 10. 六类信道规划

### 10.1 AWGN

**目的**：复基带回归、S3/S4 基线、其他信道相对退化参考。

模型：

```text
y[k] = x[k] + nI[k] + j*nQ[k]
nI,nQ ~ N(0,sigmaSquared)
LLR[k] = 2*real(y[k])/sigmaSquared
```

接收机：只用原 BPSK 实轴；Q 路不进入译码。

公平性：同组 CC/LDPC 共享 frameIndex 和母噪声前缀；不同 Ntx 只读取各自所需前缀。

C++：复 BPSK、复 AWGN、实轴投影、LLR。

MATLAB：固定向量逐元素验证 BPSK、I/Q 噪声、y、LLR；CC 继续逐 bit；LDPC 固定 codeword 后只验证信道前端。

中间输出：payload、codeword、complex symbols、zI/zQ、rx、LLR、decoded payload。

Smoke Gate：

- 无噪声恢复 300 bit；
- `zQ=0` 时新链路与使用同一 zI 的实链路逐元素一致；
- 复链路实轴 LLR 与参考误差满足容差；
- 曲线与 S3/S4 历史 AWGN 合理一致，不要求逐帧历史相同。

Formal：统一 31 点。

风险：误用旧 Common Eb/N0 API；I/Q 方差重复除 2。

### 10.2 固定多径 + 已知信道 MMSE

**目的**：比较两种编码对符号间干扰和均衡残差的耐受度。

冻结 profile：

```text
profileId = fixed_1_065_035_d0_1_3
rawTaps = [1.0,0.65,0.35]
delaysSymbols = [0,1,3]
rawEnergy = 1.545
normalizedTap[l] = rawTap[l]/sqrt(1.545)
linearConvolution = true
observationLength = Ntx + 3
receiverKnowsChannel = true
equalizer = linear MMSE
```

模型：

```text
r = Hx + n
A = (H^H H + sigmaSquared I)^(-1) H^H
xHat = A r
G = A H
```

LLR 冻结为逐符号对角高斯近似：

```text
gk = real(G[k,k])
vk = sum(j!=k, |G[k,j]|^2) + sigmaSquared*sum(m, |A[k,m]|^2)
LLR[k] = 2*gk*real(xHat[k])/vk
```

`vk<=0`、NaN、Inf 立即 Gate 失败。该定义显式包含残余 ISI 和均衡噪声增强，不允许直接套用 AWGN 的 `2*xHat/sigmaSquared`。

接收窗口：保留完整 `Ntx+3` 线性卷积观测；输出严格恢复 Ntx 个均衡符号。

随机性：信道固定，只有 payload 和 AWGN 随 frame 变化。

公平性：同 profile、同 Es/N0、同 frameIndex、同相对噪声位置。

C++：复数 H/A/G 构造、Cholesky/稳定求解、LLR。

MATLAB：逐元素比较 normalized taps、H、r、A、xHat、gk、vk、LLR。

Smoke Gate：

- `[1], delay[0]` 退化为 AWGN；
- 无噪声固定三径恢复通过；
- H/A/G 维度和尾部一致；
- C++/MATLAB 浮点误差通过；
- post-equalization hard BER 不劣于 pre-equalization。

Formal：统一 31 点。

主要指标：BER、FER、均衡时间、LLR 时间、decode 时间、total receiver 时间、channelLossDb。

风险：正规方程条件数、复数共轭错误、残余 ISI 高斯近似。

### 10.3 CFO

**目的**：比较无同步补偿时对整帧相位漂移的敏感度。

模型：

```text
phi[k] = k*(pi/6)/(Ntx-1)
r[k] = x[k]*exp(j*phi[k]) + n[k]
endPhaseRotationDeg = 30
normalizedCfo = 1/(12*(Ntx-1))
```

接收机：

- 不估计、不补偿 CFO；
- 统一取 `real(r[k])`；
- 使用 nominal AWGN LLR `2*real(r)/sigmaSquared`；
- 禁止使用 `abs(r)`。

公平性：不同 Ntx 的 normalizedCfo 不同，但整帧累计相位统一 30°。

C++/MATLAB：逐元素比较 phi、旋转后符号、加噪结果、投影和 LLR。

Smoke Gate：

- 0° 逐元素退化为 AWGN；
- 首符号 0°、末符号 30°；
- CC/LDPC 使用完全相同投影和 LLR 规则；
- bit mismatch 为 0。

Formal：30° 主 case，统一 31 点。

风险：把角度当弧度、使用 Ntx 而不是 Ntx-1、误做相位补偿。

### 10.4 多普勒

**目的**：研究帧内瞬时频偏随位置变化造成的非线性相位轨迹；不得等同固定 CFO。

候选单径模型：

```text
epsilon[k] = dopplerSpan*(k/(Ntx-1)-0.5)
phi[0] = 0
phi[k+1] = phi[k] + 2*pi*epsilon[k]
r[k] = x[k]*exp(j*phi[k]) + n[k]
epsilonCenter = 0
initialPhase = 0
amplitude = 1
dopplerSpan = 2/(3*(Ntx-1)) cycle/symbol
```

选择依据：该 Ntx 归一化候选使帧中部相位偏移量约为 30°，与 CFO 的 30°量级一致，但轨迹具有曲率且瞬时频偏变号。Stage06 必须输出四个 Ntx 的精确最大相位偏移，不得只写“约 30°”。

接收机：不估计、不补偿；原 BPSK 实轴投影；nominal AWGN LLR。

随机性：主 Formal 无随机 Doppler 参数；payload/noise 随 frame 变化。

MATLAB：逐元素比较 epsilon、phi、旋转符号、rx、LLR。

Smoke Gate：

- dopplerSpan=0 退化 AWGN；
- 相位轨迹非线性且瞬时频偏过零；
- 无 NaN/Inf；
- 1～6 dB grid 不是全 FER≈1、全 FER≈0 或与 AWGN 全重合。

Formal：仅在 grid smoke Gate 通过后使用上述唯一候选。

风险：当前工程没有冻结依据；离散求和端点存在轻微 Ntx 依赖；这是必须由用户确认的新参数。

### 10.5 短时遮挡

**目的**：比较连续信号缺失对不同码结构的影响，作为无交织基线。

模型：

```text
y[k] = a[k]*x[k] + n[k]
a[k] = 0 inside blockage, otherwise 1
blockageFraction = 0.10
blockageLength = round(0.10*Ntx)
oneBlockagePerFrame = true
noWrap = true
AWGN remains active
noInterleaving = true
```

起点：

```text
u = deterministicUniform(masterSeed, channelId, frameIndex)
relativeStart = u
start = floor(relativeStart*(Ntx-blockageLength+1))
```

同一 frameIndex 的两种编码共享 `relativeStart`，而不是强行共享绝对 symbol index。

接收机：已知 a[k]；匹配 LLR：

```text
LLR[k] = 2*a[k]*real(y[k])/sigmaSquared
```

遮挡区 LLR 精确为 0，表示擦除。固定绝对长度只作为辅助 smoke，不进入主 Formal。

MATLAB：逐元素比较 length、start、mask、rx、LLR。

Smoke Gate：

- fraction=0 退化 AWGN；
- length 取整、起点合法、不回绕；
- mask 中 0 的数量精确等于 blockageLength；
- 相同 relativeStart Gate 通过。

Formal：10% 唯一主参数，统一 31 点。

风险：已知 mask 是理想接收机假设，最终报告必须明确，不能推广为未知遮挡检测性能。

### 10.6 连续突发干扰

**目的**：建立 CC/LDPC 软信息链路公平的无交织突发基线。

BCH S2 的历史主模型是译码前连续 bit 翻转且无 AWGN，不直接复用为 S5 主模型。

S5 主模型：

```text
r[k] = x[k] + n[k] + b[k]*w[k]
burstFraction = 0.05
burstLength = round(0.05*Ntx)
oneBurstPerFrame = true
noWrap = true
noInterleaving = true
burstInterferenceToSignalDb = 10.0 dB
beta = sqrt(10^(10/10))
wI,wQ ~ N(0,1), independent deterministic channel-state noise
```

起点使用与遮挡相同的 relativeStart 规则，但使用独立 `channelStateGroupId`。

接收机：

- 不检测突发区间；
- 不做干扰消除；
- 使用 nominal AWGN LLR `2*real(r)/sigmaSquared`；
- 因此该实验测试编码面对未建模强连续干扰的鲁棒性。

公平性：同 frameIndex、relativeStart、wI/wQ 前缀、burstFraction 和 ISR。

MATLAB：逐元素比较 start、mask、干扰样本、rx、LLR。

Smoke Gate：

- fraction=0 或 ISR=`-Inf` 的实现专用退化 case 等于 AWGN；
- 长度、起点、不回绕准确；
- CC/LDPC 相对起点相同；
- 1～6 dB grid 不是全饱和或完全无影响；
- 不把 bit flip、LLR 擦除混入主 case。

Formal：5%、10 dB ISR 的唯一主 case；参数只允许按第 13.3 节规则修正一次。

风险：10 dB ISR 没有历史冻结依据，需用户确认；独立干扰噪声策略必须版本化。

## 11. 公共帧池、噪声池与信道状态

所有 fixed-vector C++/MATLAB 对比必须检查：

```text
framePoolId
framePoolOverallHash
noisePoolId
noisePoolOverallHash
frameIndex
payloadLength
noisePolicyVersion
complexNoisePolicyVersion
channelStateHash
configHash
bitOrder
```

Formal 允许按同一确定性算法即时生成噪声，不要求保存 50000 帧完整池，但 C++ 与 MATLAB fixed-vector 必须读取同一小型 fixture。

信道状态 canonical hash 至少覆盖：

```text
channelType, profileId, Ntx, frameIndex, damageLength, relativeStart,
taps, delays, endPhase, dopplerSpan, ISR, seeds, policyVersions
```

## 12. MATLAB 验证边界

### 12.1 CC

允许使用 `poly2trellis`、`convenc`、`vitdec`，但必须冻结：

- K=7、171/133 八进制；
- 状态编号和 bit 顺序；
- 初始状态 0、尾比特 6；
- R2/3 打孔图样与位序；
- complete/truncated/term 模式；
- soft input 定义、符号和缩放；
- traceback；
- 行/列向量方向。

逐 bit 必须 0 mismatch：

```text
payload, encoderInput, tail, motherCode, punctured/transmitted,
hardDecision, decodedPayload, bitErrorMask
```

### 12.2 LDPC

不使用 MATLAB 官方 LDPC 编码器替换 Direct 编码器；不要求官方 LDPC 译码器与 NMS 逐 bit 一致。

验证范围：

```text
读取固定 C++ codeword
-> BPSK
-> channel impairment
-> AWGN
-> equalization/projection
-> LLR
```

最终 LDPC 解码由 C++ 自回归、syndrome、payload 和统计 Gate 验证。

### 12.3 预先冻结容差

| 对象 | absTol | relTol |
|---|---:|---:|
| AWGN/CFO/Doppler/遮挡/突发逐元素 | 1e-12 | 1e-10 |
| 多径 H/A/G/xHat/v/LLR | 1e-10 | 1e-9 |
| bit/hash/长度/起点 | 0 | 0 |

失败后不得临时放宽；若算法顺序导致可解释差异，必须归档并通过新的 Stage 规格冻结修改容差。

## 13. Smoke、公式审计与参数修正

### 13.1 `formula_audit.md` 格式

每个信道 Stage 必须记录：

| 字段 | 内容 |
|---|---|
| formulaId/name | 稳定标识和中文名 |
| expression | 数学表达式 |
| physicalMeaning | 物理含义 |
| units | 每个参数单位 |
| cppFunction | C++ 函数和文件 |
| matlabFunction | MATLAB 函数和文件 |
| fixedInput | 固定数值样例 |
| independentReference | 手算或 Python 高精度值 |
| cppOutput/matlabOutput | 实际输出 |
| absError/relError | 误差 |
| absTol/relTol | 预冻结容差 |
| status | PASS/FAIL |

至少覆盖 BPSK、Es/N0、sigma、I/Q 方差、LLR 符号、actualRate、Eb/N0、三径归一化、卷积、MMSE、均衡增益/方差、CFO、多普勒、遮挡、突发、BER/FER、停止和鲁棒性指标。

### 13.2 Fixed-vector smoke

参数：

```text
Es/N0 = [1.0,3.5,6.0] dB
frameIndex = 0..9
每信道每 case：
  no impairment + no noise
  impairment + no AWGN
  impairment + AWGN
```

保存完整 trace；不使用 Monte Carlo 停止条件。

### 13.3 Grid smoke

```text
Es/N0 = 1.0..6.0 dB, step 0.5, 11 points
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
```

同一公平组配对停止：双方使用相同 frameStart/frameCount；只有双方在 `processedFrames>=1000` 后均达到 200 个错误帧才提前停止，否则共同运行至 50000。

只保存 summary、checkpoint、配置/hash、每点前 3 帧完整 trace和每点前 10 个异常帧 trace。

取消独立 Prescan，因为 Formal SNR 网格已固定，参数强度筛选由 grid smoke 承担。

允许一次参数修正的触发条件：

- 11 点全部 FER>=0.99；
- 11 点全部 FER=0；
- 复杂信道与 AWGN 的每点 FER 差均小于双方 Wilson 95% 区间半宽；
- NaN/Inf；
- 补偿/均衡 Gate 失败；
- 单 scheme-point 预计超过 2 小时。

修正规则：

1. 归档当前 results/config/report；
2. 写明原因和数据；
3. 多普勒只允许把最大相位偏移从 30°改为 15°或 45°之一；
4. 突发 ISR 只允许从 10 dB 改为 6 dB或 14 dB之一；
5. 只重跑对应信道 grid smoke；
6. 第二次仍失败则 BLOCKED，不继续 Formal。

## 14. Formal 规划

```text
Es/N0 = -5.0..10.0 dB
step = 0.5 dB
31 points
minFrames = 1000
targetFrameErrors = 200
maxFrames = 50000
checkpointIntervalFrames = 1000
```

任务键：

```text
comparisonGroup/channel/case/esN0Db/frameStart/frameCount/configHash
```

必须支持：

- checkpoint/resume；
- frame shard；
- 原子 checkpoint；
- 重复任务拒绝；
- 缺失/重复 SNR 点拒绝；
- config/channelState/framePool/noisePolicy hash 校验；
- continuous 与 resume 计数、hash 一致；
- 异常终止 `ERROR_ABORT`；
- stopReason；
- 合并前 frame 区间连续且无重叠。

Formal 不逐帧运行 MATLAB。

## 15. 指标和鲁棒性

### 15.1 可靠性

```text
BER = payloadBitErrors/(processedFrames*300)
FER = payloadErrorFrames/processedFrames
payloadSuccessRate = 1-FER
decoderFailureRate
undetectedErrorRate
Wilson 95% CI
```

### 15.2 相对 AWGN

```text
deltaFer(channel,gamma) = FER_channel(gamma)-FER_awgn(gamma)
channelLossDb(target) =
  EsN0_channel(FER_target)-EsN0_awgn(FER_target)
FER_target in {1e-1,1e-2}
```

只在两条真实曲线共同覆盖目标 FER 时做相邻点 log(FER) 线性插值；禁止外推。

### 15.3 时延与稳定性

```text
channelProcessingTimeUs
equalizationTimeUs
frequencyCompensationTimeUs
llrGenerationTimeUs
avgDecodeTimeUs
p95DecodeTimeUs
maxDecodeTimeUs
totalReceiverAlgorithmTimeUs
LDPC avgIterations
LDPC maxIterationFrameRate
decoderFailureRate
undetectedErrorRate
```

计时排除文件 I/O、日志、CSV、配置解析、帧池/噪声池读取和绘图。

### 15.4 鲁棒性定义

鲁棒性是相对 AWGN 维持可靠性、时延和译码稳定性的能力，不构造任意加权总分。每个信道输出：

- 同 Es/N0 的绝对 FER 排名；
- deltaFer 排名；
- 可计算时的 channelLossDb；
- decode latency 排名；
- total receiver latency 排名；
- 推荐方案和代价。

## 16. 绘图规划

只使用折线图和表格，不使用柱状图：

- BER vs Es/N0；
- FER vs Es/N0；
- avg decode time vs Es/N0；
- P95 decode time vs Es/N0；
- total receiver time vs Es/N0；
- LDPC avg iterations vs Es/N0；
- deltaFer vs Es/N0。

BER/FER 对数纵轴；时间/迭代线性纵轴。

每张图输出：

```text
PNG
figure_data.csv
plot_manifest.json
plot_check.md
SHA256
```

禁止平滑、修改原始数据、补点、伪造零值或人为 error floor。CSV 中真实 0 保留；对数图不画 0；真实性能平台必须保留。

## 17. 目录结构

新增 `Task/Comparison/S5/` 的理由：S5 同时依赖 CC 与 LDPC，归属任一编码目录都会造成跨模块越界；Comparison 是跨编码实验的单一责任目录。

```text
Task/Comparison/S5/
├─ S5_initial_execution_plan.md
├─ current/
│  ├─ include/s5_comparison/
│  ├─ src/
│  ├─ tests/
│  ├─ matlab/
│  ├─ scripts/
│  └─ configs/
└─ stages/
   ├─ stage01_scope_and_case_freeze/
   ├─ stage02_complex_baseband_foundation/
   ├─ stage03_awgn_regression/
   ├─ stage04_multipath_channel/
   ├─ stage05_cfo_channel/
   ├─ stage06_doppler_channel/
   ├─ stage07_short_blockage_channel/
   ├─ stage08_burst_interference_channel/
   ├─ stage09_smoke_validation/
   ├─ stage10_formal_multichannel_simulation/
   └─ stage11_plot_audit_and_final_integration/
```

每个 Stage 按用户本轮要求规划：

```text
results/              # 默认不提交大结果
archive/
readme.txt
stage_plan.md
changed_files.md
validation_report.md
known_issues.md
frozen_config.csv
commands_used.md
manifest.json
changes.patch          # 用户本轮明确要求，必须由真实 functional range 生成
```

manifest 必须记录本 Stage 自己的 functional range，批次分支不得用整个 `main...HEAD` 代替。

## 18. Stage 目标、输入、输出和 Gate

| Stage | 目标/输入 | 主要输出 | Gate |
|---|---|---|---|
| 01 scope | 本文、S3/S4 冻结记录 | case/接口/参数冻结、验收矩阵 | `PASS_S5_SCOPE_FREEZE` |
| 02 complex | Common v1 + 复噪声需求 | 复 BPSK、I/Q policy、接口、公式审计 | `PASS_S5_COMPLEX_BASEBAND` |
| 03 AWGN | 四个 case | 新旧 AWGN 等价、S3/S4 回归 | `PASS_S5_AWGN_REGRESSION` |
| 04 multipath | 三径 profile | H/MMSE/LLR、MATLAB 固定向量 | `PASS_S5_MULTIPATH` |
| 05 CFO | 0°/30° | 相位、投影、LLR 固定向量 | `PASS_S5_CFO` |
| 06 Doppler | span 候选 | 轨迹、固定向量、参数候选 | `PASS_S5_DOPPLER` |
| 07 blockage | 10% | mask/relative start/LLR | `PASS_S5_BLOCKAGE` |
| 08 burst | 5%、10 dB ISR | 干扰链路、无交织固定向量 | `PASS_S5_BURST` |
| 09 smoke | 6 信道、4 case | fixed-vector + grid smoke、final config | `PASS_S5_SMOKE` |
| 10 formal | 冻结配置 | 744 scheme-points、checkpoint/merge | `PASS_S5_FORMAL` |
| 11 integration | Formal CSV | 图、表、鲁棒性结论、总审计 | `PASS_S5_FINAL_INTEGRATION` |

Gate 依赖严格串行：前一 Stage FAIL/BLOCKED，禁止开始后续 Stage。

## 19. 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 四个代表 case | Stage01 | 长度/码率/参数对照 | 未冻结 case 拒绝 | 全字段匹配 S3/S4 |
| Es/N0 | Stage02/03 | 固定数值公式 | 把 Es 值传 Eb API 拒绝 | 公式误差通过 |
| 复噪声 | Stage02 | I/Q hash与方差 | 长度<2Ntx拒绝 | policy/hash一致 |
| AWGN | Stage03 | 新旧实轴等价 | Q复用I拒绝 | bit/float Gate |
| 多径 | Stage04 | identity与三径 | 错 delay/奇异矩阵 | MATLAB一致 |
| CFO | Stage05 | 0°/30° | 度/弧度、Ntx分母错误 | 首末相位正确 |
| Doppler | Stage06 | 0 span/候选 | 线性相位冒充 Doppler | 轨迹和 smoke 合理 |
| 遮挡 | Stage07 | 0%/10% | 回绕/越界 | mask/hash正确 |
| 突发 | Stage08 | 0%/5% | 混入bit flip/交织 | ISR/mask/hash正确 |
| MATLAB | 03–08 | fixed-vector | 独立随机输入拒绝 | bit 0 mismatch |
| paired stop | Stage09/10 | 双方同步停止 | 单方提前停止拒绝 | frameRange相同 |
| resume/merge | Stage09/10 | continuous等价 | hash/重叠/缺失拒绝 | 计数/hash一致 |
| 绘图 | Stage11 | figure-data hash | 平滑/补零/柱状图拒绝 | plot audit PASS |

## 20. Archive 规则

不得删除或覆盖旧结果。每轮修改前将上一轮当前 Stage 结果移入：

```text
archive/vNN_yyyymmdd_before_short_reason/
```

要求：英文小写、下划线、无空格、两位版本号。归档至少含 results、frozen_config、plot_manifest、validation_report、run_log、archive_manifest，并计算 SHA256。

归档属于后续 Stage 操作；本轮没有移动任何文件。

## 21. Git 工作流

1. 当前规划文件位于用户创建的 `S5-Compare`。
2. 功能实现默认分支名应为 `stage01-s5-multichannel-comparison`，从最新干净 `main` 创建。
3. 如果用户授权 `S5-Compare` 作为 Stage01–11 批次分支，必须在每个 Stage manifest 记录独立 functional range。
4. 禁止 `git add .`、直接修改 main、自动 merge、删除分支、force push、reset hard、clean、rebase、amend、`--no-verify`。
5. 只有用户明确要求时 commit/push。
6. commit message 使用中文：`模块/阶段：简短说明`。
7. 是否合并 `main` 始终由用户决定。

## 22. 预计计算规模与磁盘风险

### 22.1 计算规模

Formal：

```text
2 groups * 2 schemes * 6 channels * 31 SNR = 744 scheme-points
frame lower bound = 744,000
frame upper bound = 37,200,000
```

按四种 Ntx 平均约 548 symbol 估算，上限约 20.4×10^9 个发送 symbol 进入信道前端；多径 MMSE 和 LDPC NMS 是主要耗时项。

Grid smoke：

```text
2*2*6*11 = 264 scheme-points
264,000..13,200,000 frames
```

Fixed-vector 最大约 2160 个 scheme-frame trace。

### 22.2 磁盘

- 50000 帧、1280 float64 实样本的单个复噪声池约 512 MB；
- 不为每个信道复制母噪声池；
- Formal 不保存全帧 trace；
- 每点只保存前 3 帧和前 10 异常帧；
- 目标是 S5 活跃生成资产小于 5 GB；
- 若预估超过 5 GB，Stage09 Gate BLOCKED，必须减少 trace，不得删除旧结果腾空间。

## 23. 工具箱和实现风险

### 23.1 MATLAB

- CC fixed-vector 依赖 Communications Toolbox 的 `poly2trellis/convenc/vitdec`；
- LDPC 信道前端参考只需基础 MATLAB 复数、矩阵运算；
- 若 Communications Toolbox 不可用，CC 官方参考 Gate 为 BLOCKED，不能用自写 MATLAB 冒充官方函数通过；
- 本轮未启动 MATLAB，版本和 license 状态需在 Stage03 记录。

### 23.2 C++ 复数运算

- 必须使用 `std::complex<double>` 的共轭转置；
- BPSK 符号能量必须保持 1；
- I/Q 每维方差均为 sigmaSquared；
- 多径 normal equations 条件数和 Cholesky 正定性必须记录；
- 核心循环预分配 H/A/G 工作区，不得逐帧重复构造固定矩阵。

### 23.3 多普勒

参数没有历史冻结依据；候选是基于与 CFO 同量级相位偏移的工程归一化，不代表物理载频/速度模型。最终报告只能称“单径线性变频相位模型”。

### 23.4 多径 LLR

对角高斯近似忽略均衡输出间相关性。必须保存 `gk/vk` 分布，并在 known issues 中说明。若 smoke 显示 LLR 标度异常，只允许修复公式实现，禁止以任意缩放因子调曲线。

## 24. 尚待用户确认

1. 是否确认主 Formal 的 CC 使用完整块 Soft Float，而不是 S3 的真滑窗工程推荐？
2. 是否授权当前非标准命名分支 `S5-Compare` 作为 Stage01–11 批次分支，还是 Stage01 另建 `stage01-s5-multichannel-comparison`？
3. 是否接受多普勒候选 `dopplerSpan=2/(3*(Ntx-1))`，对应约 30°中部相位偏移？
4. 是否接受突发主参数 `burstFraction=0.05`、`ISR=10 dB`、未知突发区间、nominal LLR？
5. 是否接受遮挡接收机已知 mask、遮挡区 LLR=0 的理想假设？
6. 是否确认多径采用本文的 `gk/vk` 对角高斯近似 LLR？

以上任一项改变都必须在 Stage01 规格冻结中留下用户确认和参数版本，不能在 Smoke 中暗改。

## 25. 第 2 次 Codex 提示词执行边界

第 2 次只允许执行 Stage01–09：

```text
读取用户批准的本规划
-> 确认分支与 functional range
-> 逐 Stage 规格冻结
-> 实现复基带和六信道
-> 单元/负向测试
-> C++/MATLAB fixed-vector
-> formula audit
-> grid smoke
-> 一次受限参数修正（若触发）
-> 输出 S5_SMOKE_READY_FOR_REVIEW
-> 停止
```

禁止 Formal、科研绘图、最终结论、自动进入第 3 次任务。默认不 commit/push，除非用户明确要求。

## 26. 第 3 次 Codex 提示词执行边界

第 3 次只在 `PASS_S5_SMOKE` 且 Formal 配置冻结后：

```text
审计 smoke archive/hash
-> 执行 Stage10 Formal
-> checkpoint/resume/shard/merge 审计
-> Stage11 原始数据审计
-> 折线图和结果表
-> 鲁棒性与场景推荐
-> 功能提交
-> manifest/validation/known issues 审计收口
-> 按用户授权 push
-> 远程验证
-> 停止
```

禁止扩大算法范围、重做 S3/S4、加入交织、自动合并 main 或自动开始 S6/S7。

## 27. 本轮 Gate

本轮只审计并创建本文件：

| 检查 | 状态 |
|---|---|
| 仓库/分支/Git 状态已记录 | PASS |
| 老师 PDF/DOCX 与 S5 对应关系已核对 | PASS |
| S3/S4 已进入 main | PASS |
| S2 五类信道真实模型已核对 | PASS |
| Common 容量与公式差异已记录 | PASS |
| 六信道、Smoke、Formal、Stage、Gate 已规划 | PASS |
| 本轮编译/测试/Smoke/Formal | NOT_RUN_BY_SCOPE |
| 本轮 commit/push/merge | NOT_PERFORMED_BY_SCOPE |

本文件批准前不得开始 Stage01 功能实现。

## 28. 用户审查与正式批准记录

审查日期：2026-07-31

### 28.1 已批准事项

1. S5 主 Formal 的卷积码采用完整块 Soft Float：
   - `CC_R23_BLOCK_FLOAT`；
   - `CC_R12_BLOCK_FLOAT`。
2. 当前 `S5-Compare` 分支授权作为 S5 Stage01～Stage11 的批次功能分支；每个 Stage 必须记录独立 functional range。
3. 多普勒采用单径线性时变频偏相位模型：
   - 不称为真实卫星多普勒模型；
   - Smoke 输出各 Ntx 的完整相位轨迹审计字段；
   - 只有 grid smoke Gate 通过后才允许进入 Formal。
4. 短时遮挡采用 `blockageFraction=0.10`、理想已知遮挡 mask、遮挡区 `LLR=0`；结论限定为已知连续擦除场景。
5. 多径采用已知信道实轴线性 MMSE，以及 `gk/vk` 逐符号对角高斯近似 LLR。
6. 突发干扰采用 `burstFraction=0.05`、ISR=10 dB、接收端未知突发 mask、nominal AWGN LLR、无交织。

### 28.2 强制公式和实现修正

1. ISR 定义为复干扰总功率除以 BPSK 符号功率：

   ```text
   beta = sqrt(10^(ISR_dB/10)/2)
   ```

   `wI,wQ~N(0,1)` 时，`E[|beta(wI+jwQ)|^2]=10^(ISR_dB/10)`。禁止使用未除以 2 的 beta。
2. 固定实系数多径使用实轴 MMSE：

   ```text
   A = (H^T H + sigmaSquared I)^(-1) H^T
   ```

   不使用当前未澄清噪声协方差的复 MMSE 正则项。
3. 无 AWGN fixed-vector case 不计算 `LLR=2y/0`。无噪声译码的冻结有限软度量为：发送 bit 0 使用 `+100`，发送 bit 1 使用 `-100`；经过确定性损伤后按接收实轴符号使用 `sign(real(y))*100`，精确零值使用 0。
4. Common-04 旧噪声策略保持不变。S5 在自身目录新增在线复噪声策略 `s5_complex_pair_v1`；不生成完整 50000 帧复噪声池。

### 28.3 执行授权与停止点

批准第 2 次 Codex 执行 Stage01～Stage09：代码实现、公式审计、fixed-vector smoke、grid smoke 和 Formal 参数冻结。未经 `PASS_S5_SMOKE` 不得进入 Formal；本轮即使通过也必须停止，等待第 3 次执行授权。

PLAN_APPROVED_FOR_STAGE01_TO_STAGE09
