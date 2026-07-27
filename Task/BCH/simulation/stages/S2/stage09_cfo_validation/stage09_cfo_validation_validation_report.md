# stage09_cfo_validation 验证报告

Gate：`PASS_STAGE09_CFO_VALIDATION`

- Release 构建成功；CTest 1/1 PASS。
- 4 符号固定向量覆盖 0°、10°、20°、30°，正负 BPSK 与固定复噪声。
- MATLAB 使用 `k=i-1` 独立复算；连续值最大误差不超过 `1e-12`，hard-bit mismatch=0。
- 八个 stage02 Case 的首相位为 0、末相位为 π/6，且增量均按各自 encodedLength 计算。
- 八 Case 的 24 帧连续执行、11+13 resume、8+8+8 shard/merge 整数统计和噪声校验和一致。
- 0°时实部为 stage06 的 `x+sigma*zI`，硬判决及译码链路完全退化一致。
- stage10 的 30°模型、复噪声方差、停止规则和 K200/K300 初始 trial 网格已冻结。
- 未出现 mismatch、NaN 或 Inf。

功能范围：`8bd58cf80c60f2d373d479b9d8e02a1919fdca8d...0ba060c4aff4fe03fee0085e380cd789d1d52b64`。
