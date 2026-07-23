# BCH-16V validation report

## 环境与官方函数

- MATLAB：24.2.0.2712019 (R2024b)，PCWIN64。
- Communications Toolbox：24.2。
- 实际调用：`bchgenpoly`、`bchenc`、`bchdec`。
- 参数审计：BCH(15,11) generator degree=4、t=1；BCH(255,207) generator degree=48、
  t=6、primitive polynomial=0x11D。

## 输入与配置 Gate

- BCH-15 正式摘要 SHA-256：
  `87e28f91254828adb1f6989d9ceecab25cf204d8e4f3ee38f4b9e5fb10666373`。
- Common payload manifest SHA-256：
  `be5cf397cc1ea0d566ff9a4900ed30e17af273ed84986a6a48f9eb3db2f1dc71`。
- payload overall hash：
  `b1b0d61565e4234cd8585110940c6f646d42beca0abc0cbb048ba0368bb50805`。
- S200：21 点，321,435 帧；B200：14 点，253,308 帧；合计 574,743 帧。
- 逐点 SNR、processedFrames、payloadLength、encodedLength、frameRate、sigma 和标准高斯输入
  hash 均通过检查。

## 三层验证

1. 固定向量：两种 Case 共 212 个向量，官方编码 mismatch=0 帧/0 bit。
2. 代表/正式 hard-decision 帧：保证纠错能力内 mismatch=0 帧/0 bit。
3. 完整正式曲线：35/35 点完成，processedFramesMismatch=0。

超能力范围出现 3 个 decoded payload 差异帧，全部已逐点分类。C++ 与 MATLAB 的 frame-error
判定无分歧，配对 disagreement=0；最大 BER 绝对差 `4.000000000000531e-06`，最大 FER
绝对差 0，全部 Wilson 95% FER 区间重叠。

目标 FER 插值差：

- S200：FER=1e-1 为 0 dB；FER=1e-2 为 0 dB；FER=1e-3 未共同夹住，不外推。
- B200：FER=1e-1、1e-2、1e-3 均为 0 dB。

## 图形 Gate

- PNG 数量：4。
- 非 PNG 图形产物：0。
- 每图均有 figure-data CSV，PNG SHA-256 与 plot manifest 一致。
- matplotlib：3.10.7，Agg backend，dpi=240。

## 历史回归

- Common CTest：7/7 PASS。
- BCH-01～06 分段 CTest：14/14 PASS；BCH-06 MATLAB cross-check PASS。
- BCH-07～10 整块 CTest：1/1 PASS；参数、GF、frame pool、detail、非法输入和官方 toolbox
  codec checker 全部 PASS。
- BCH 第 4 组当前构建 CTest：7/7 PASS。


## ???????

- ?????`24866f55ab36a513cd23e3896fcecc1f657240ee`?
- C++ ? MATLAB Official ?????????C++ ???????????MATLAB Official ????????????
- S200 BER?S200 FER?B200 FER ? plot values ????????? exact-overlap ???B200 BER ?????????????????????
- ????? PNG ? plot manifest???????? MATLAB/C++ ?????? BCH-15 ????? BCH ?????

## Gate

`PASS_BCH16V_MATLAB_OFFICIAL_AWGN_CURVE_REFERENCE`

本 Stage 未修改 BCH-15 正式结果，未进入交织实验，未合并 main。

