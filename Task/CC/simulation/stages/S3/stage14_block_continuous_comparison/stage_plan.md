# stage14_block_continuous_comparison 2026-07-29 修订规格冻结

## 目标

实现四种组织、三码率的真实逐 slot 到达、在线滑窗触发和完整正式曲线。

## 公共冻结参数

- payloadBits = 300；K=7；生成多项式 171/133（八进制）；母码率 1/2；打孔码率 2/3、3/4。
- BPSK：0→+1，1→-1；横轴 `SNR = Es/N0 (dB)`。
- `sigmaSquared = 1/(2*10^(snrDb/10))`；`actualRate=payloadBits/transmittedBits`。
- `ebN0Db=snrDb-10*log10(actualRate)`；正式 CSV 记录 SNR、种子、case/sourceNoise、CI 和停止原因。
- coarse：-5～10 dB、0.5 dB；停止规则 1000/200/50000；dense 优先 0.1 dB。
- 只允许修改 `Task/CC/**`，禁止修改 BCH、LDPC、Common、main 或公共 SNR 定义。

## 非目标

- 不新增 200-bit 正式实验。
- 不把符号级离散 BPSK-AWGN 描述为连续波形仿真。
- 不合并 main，不删除旧 Stage，不用预扫描或旧错误结果冒充 formal。

## 接口与数据

输入由 Stage09 正式基线、共享 payload/噪声标识和本 Stage 冻结配置组成；输出为原始 CSV、汇总 CSV、figure-data、PNG、plot manifest/check，以及可复现命令和审计文件。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 本 Stage 功能 | `stage14_block_continuous_comparison/src` 与 `scripts` | 每 slot 到达即推进解码并记录 bit/source/decision 时标、边界、缓存、吞吐。 | 拒绝完整 rx 拼接后一次 decode、错误时延公式或 Block 伪 boundaryBER=0。 | Stage12 先通过；372 coarse 点、候选 dense、在线证据和六类主图通过。 |
| 公平性与统计 | runner/checker | 同帧同噪声、CI、停止规则和 SNR 公式复算 | 篡改种子、缺字段、NaN/Inf、未覆盖插值 | checker 全通过 |
| 科研绘图 | `results` 与绘图脚本 | PNG/figure-data/hash 可复算 | 平滑、外推、零错误伪装非零 | plot check 全通过 |

## 当前临时状态

`BLOCKED`。只有本文件所列 Gate 实际通过后才更新最终状态。
