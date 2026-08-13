# BCH 正式数据质量审计

对 6 个正式主 CSV 共 1890 行执行逐行复算；另检查 W9 六个图源 CSV 共 222 行。

- `payloadBits=frames*payloadLength`：全部通过。
- `BER=payloadErrorBits/payloadBits`、`FER=payloadErrorFrames/frames`：全部通过。
- `trueSuccessFrames+payloadErrorFrames=frames`：全部通过。
- `reportedSuccessFrames+decoderFailureFrames=frames`（缺省时由状态计数等价复算）：全部通过。
- `miscorrectedFrames<=reportedSuccessFrames`：全部通过。
- `actualRate=payloadLength/encodedLength`：全部通过。
- S1 W9 图源 `Es/N0=sourceEbN0+10log10(R)`：222/222 通过。
- Stage10/12/16 S2 横轴转换：全部通过。
- Stage07/08 的 `snrDb` 与所需 Es/N0 固定相差 +3.0102999566 dB，原因是其方差定义使用 `sigma²=1/snrLinear`，该字段表示 `2Es/N0`；记录为口径问题，不是数值计数错误。

原始零错误点均保留为 0。Stage07 验证报告明确将有限样本上界与主曲线分开并避免伪造高 SNR error floor；本轮未替换任何零值、未添加水平线。曲线合理性沿用各正式 Stage checker，未发现 NaN/Inf 或计数越界。

结论：计数、码率和状态 Gate 通过；统一 Es/N0 图轴 Gate 对 Stage07/08 为“转换后通过”，原图未经转换不得直接进入第4章主图。
