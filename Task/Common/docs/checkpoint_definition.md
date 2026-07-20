# checkpoint 字段定义

Common-01 只冻结 checkpoint 字段，不实现读写和 resume。

## 必需字段

```text
stageId
runId
experimentId
caseId
snrIndex
nextFrameIndex
framesProcessed
payloadBitsProcessed
bitErrors
frameErrors
payloadSuccessFrames
decoderDeclaredSuccessFrames
undetectedErrorFrames
timingAccumulator
iterationAccumulator
configHash
framePoolHash
noisePolicyVersion
codeVersion
gitCommit
```

## 恢复前必须验证

```text
configHash
framePoolHash
caseId
SNR
noisePolicyVersion
```

若任一字段不一致，后续 Common-07 的 checkpoint/resume 实现必须拒绝恢复。

## 本阶段边界

Common-01 不实现：

- checkpoint 文件格式读写；
- resume 控制流程；
- 连续运行与恢复运行一致性测试。

这些内容由 Common-07 实现。

