# CC 结果与检查点 schema

## 兼容策略

CC 结果扩展 `Task/Common/config/result_schema.json`，不修改公共文件。公共字段 `codeRate` 在 CC 中必须等于主字段 `actualRate`。

## 点级结果

点级原始 CSV 必须包含机器可读 schema 中 `pointResultRequiredFields` 的全部字段。核心整数统计必须保留，BER/FER 必须由整数复算，不接受只有浮点比例而没有分子分母。

时延字段单位统一为微秒，吞吐字段单位统一为 Mbit/s：

```text
avgEncodeTime_us
maxEncodeTime_us
avgDecodeTime_us
p95DecodeTime_us
maxDecodeTime_us
rawDecodeThroughput_Mbps
successfulDecodeThroughput_Mbps
```

```text
normalizedGoodput = actualRate * (1 - FER)
```

## checkpoint/resume

checkpoint 必须采用原子写入策略：先写同目录临时文件，完整 flush/close 并验证后再替换目标。必须保存：

- Stage/run/experiment/case/SNR 身份；
- `nextFrameIndex` 和累计整数统计；
- 编码/译码计时累加器；
- 配置、帧池、噪声策略、代码版本和功能提交 hash；
- 连续模式所需的编码器状态、Viterbi 路径度量、幸存缓存和打孔相位。

resume 必须逐项验证身份字段。任一 hash、case、SNR 或策略不一致时拒绝恢复。恢复后从 `nextFrameIndex` 继续，禁止重复或跳过帧。

## shard/merge

每个 shard 使用互不重叠的 `[frameBegin, frameEnd)`。合并器验证：

- shard 配置 hash 相同；
- frame 范围无重叠、无空洞；
- 整数统计按加法合并；
- P95 不能用 shard P95 再平均，必须由可合并样本/直方图重建；
- 已存在正式目标文件时默认拒绝覆盖。

## 图和文件命名

所有 Stage 结果必须位于对应：

```text
Task/CC/simulation/stages/S3/stageXX_name/results/
```

文件名前缀必须为完整 Stage 名。禁止通用名称：

```text
result.csv
results.csv
figure1.png
plot.png
output.png
test.csv
```

每张科研图必须同时发布 PNG、figure-data CSV 和 plot manifest。PNG 只从原始 CSV 逐点生成，不平滑、不插值、不删除坏点。

零 BER/FER 在原始 CSV 中保持 0。绘图派生字段 `plotBER`、`plotFER` 和零错误标志单独记录；不得改写原始 BER/FER。

## 发布检查

plot checker 至少验证数据点数、有限性、公式、纵轴类型、图例唯一性、PNG 格式和 SHA256。失败时不得声明图形 Gate 通过。
