# BCH local rules

- `segmented/` 与 `block/` 必须保持独立。
- BCH 必须复用 `Task/Common` 的帧池、噪声、BPSK、AWGN、指标、checkpoint 和绘图。
- 查表译码只用于 BCH(15,11,1) segmented。
- whole-block BCH 使用 BM + Chien，不使用查表。
- BCH 码率为原始 payload 长度除以实际进入 BPSK 的编码长度。
- filler 不进入码率分子；所有实际发送编码位进入分母。
- BER/FER 只统计恢复后的原始 payload。
- 普通 AWGN 不使用交织；交织仅在突发错误 Stage 使用。
- 每个 Stage 必须遵守仓库根 `AGENTS.md` 和自身冻结文件。
- 当前 Stage 不得提前实现后续 Stage。