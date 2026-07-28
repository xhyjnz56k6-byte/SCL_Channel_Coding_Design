# stage02_case_contract 验证报告

最终 Gate：`PASS_STAGE02_CASE_CONTRACT`

## 冻结结果

- 8 个 Case 全部合法且唯一。
- 200-bit 和 300-bit 各有 4 个唯一图例和 4 个唯一样式。
- 54 个独立码块的长度、filler、shortening 和发送长度全部通过复算。
- 所有码块发送长度均不超过 1000 bit。
- 8 个 Case 的 `actualRate=payloadLength/totalEncodedLength` 全部通过。
- 每 Case 4 种 payload，共 32 组无噪声编码/恢复全部一致。
- MATLAB R2024b 对 8 个 Case 的 payload/encoded 向量和码率独立复算全部通过。
- 非法 CaseId、错误 payload 长度和错误接收长度均被拒绝。

K300_M255K207 正式冻结为两个 BCH(255,207) 缩短块：

```text
payloadPerBlock = 150|150
shorteningPerBlock = 57|57
encodedLengthPerBlock = 198|198
totalEncodedLength = 396
actualRate = 300/396
```

图例采用真实名称 `255双块300`，不再使用可能误导的 `255组帧300`。

## 失败与修复记录

前五次执行分别暴露了子工程 CTest 注册、MATLAB 列名、CSV 逗号、`|` 分隔符
自动识别和 MATLAB 列类型推断问题。每次失败后均停止，没有进入 stage03。
第六次从 Release 构建到业务 checker 完整重跑并通过。

## Git 与范围

- functional base：`49f4007e282d6f5c55ba5c0e8a390cbf436f32ac`
- functional content：`0fdafb02418e7b090540f4c78f1a0c7a7aa0c62d`
- 仅新增 `Task/BCH/simulation/stages/S2/stage02_case_contract`
- 复用既有 block/segmented 编解码源码，仅链接和调用，未修改。
- 生成的 `results/` 按项目规则保留在本地，不进入 functional commit。
- push 未获授权，因此未执行。
- `main` 未合并。
