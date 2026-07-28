# stage07_multipath_validation 规格冻结

## 目标

验证历史固定实数 FIR 多径与带状 Cholesky MMSE 在必要适配后，能够正确、
公平、可复现地服务 `stage02_case_contract` 冻结的 8 个 BCH Case，并在进入
stage08 前人工冻结正式 Eb/N0 网格。

## 非目标

- 不比较多径相对 AWGN 的性能损失，不把 `h=[1]` 用作正式性能结论。
- 不加入 CFO、相位误差、多普勒、时变衰落、信道估计误差或交织。
- 不修改旧多径实现、BCH 编解码核心、`Task/Common`、`Task/CC` 或 `Task/LDPC`。

## 范围

只新增 `Task/BCH/simulation/stages/S2/stage07_multipath_validation`。直接链接
stage01 随机/AWGN 基础、stage02 Case Contract 和既有 BCH 编解码源码。

## 冻结接口与数据

- Case 参数仅来自 `stage02::allCaseContracts()`。
- 每帧随机身份由 `masterSeed, stageId, caseId, channelModelId,
  parameterIndex, ebn0Index, frameIndex, randomDomain` 共同表达；本阶段把
  `channelModelId` 和 `parameterIndex` 编入 `stageId`。
- `R=payloadLength/totalEncodedLength`。
- `sigma2=1/(2*R*10^(EbN0_dB/10))`。
- `y=Hx+n`，`A=H^T H+sigma2 I`，通过带状 Cholesky 求解 `A*xHat=H^T y`，
  禁止显式求逆。
- 完整线性卷积长度为 `N+Lh-1`，帧外符号为零。

## Gate

只有旧代码审计、冻结模型、C++/MATLAB 卷积和 MMSE、`h=[1]`、8 Case
1000+ 无噪声帧、随机性、resume/shard、trial、stage08 网格、SHA-256 和
checker 全部通过，才输出 `PASS_STAGE07_MULTIPATH_VALIDATION`。

## 提交资产

本 Stage 明确提交源码、MATLAB/Python 工具、冻结 JSON/CSV、小型汇总结果 CSV、
比较 CSV、日志和 SHA-256 摘要。`build/`、可执行文件和临时 MATLAB 文件不提交。
这些结果均由本 Stage 当次执行产生，不包含历史 formal 数据。
