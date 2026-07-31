# Stage12 规格冻结：连续编码器

目标是在不重置中间时隙的前提下保持 encoder state 与 puncture phase；首 slot 从 state0 开始，中间不加尾比特，最后可统一加 6 个零尾，也支持完全不终止。只修改本 Stage。

接口：`ContinuousEncoder::encode_slot(payload, finalSlot, appendTailOnFinal)`；状态导入导出同时包含 encoderState、puncturePhase、slotIndex、payloadBitsProcessed、motherBitsProcessed、transmittedBitsProcessed。每个 slot 返回完整元数据。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 状态跨 slot | continuous_encoder | 三种切分等于一次性编码 | 非法状态拒绝 | bit/state 一致 |
| 统一尾终止 | encode_slot | 最后回 state0 | 中间加尾被接口禁止 | PASS |
| puncture 相位 | 三码率 | 拼接等于一次性 puncture | 相位重启检测 | PASS |
| export/import | state struct | 中途迁移后结果一致 | 非法 phase 拒绝 | PASS |
| 不终止长流 | no-tail 路径 | 拼接等于 encode_segment | 丢/重 bit 检查 | PASS |

Gate：`PASS_STAGE12_CC_CONTINUOUS_ENCODER`
