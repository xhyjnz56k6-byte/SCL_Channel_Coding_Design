# stage05_awgn_trial 规格冻结

## 目标

在不进行 prescan 的前提下，对 8 个冻结 Case 各执行 3 个手工代表 Eb/N0 点、每点
500 帧的 AWGN 试运行；验证原始计数、运行时、绘图、checkpoint/resume、分片合并及
stage06 正式停止规则基础设施。

## 非目标

- 不生成正式 BER/FER 结论；
- 不改变 stage01 随机性、stage02 Case 契约、stage03 无噪声或 stage04 纠错能力契约；
- 不执行或创建多径实验；
- 不进入 prescan。

## 范围

仅允许修改 `Task/BCH/simulation/stages/S2/stage05_awgn_trial/`。构建与试运行结果写入
`Task/BCH/simulation/build/S2/stage05_awgn_trial/` 及本 Stage 的 `results/`。

## 数据契约

- BPSK：0 映射 +1，1 映射 -1；
- 实际码率 `R=payloadLength/encodedLength`；
- `sigma2=1/(2*R*10^(EbN0Db/10))`；
- `SNRDb=EbN0Db+10*log10(2*R)`；
- 主键 `(stageId, caseId, ebn0Index, frameIndex, randomDomain)`；
- 零错误绘图替代值仅为 `0.5/denominator`，原始值保持 0。

## Gate

必须真实输出 `PASS_STAGE05_AWGN_TRIAL`，并满足 24 个试运行点、8/8 续跑、
8/8 三分片合并、正式停止规则边界测试和 4 张 300 dpi PNG 全部通过。
