# BCH 方案冻结裁定

五个核心方案均由 `bch_case_adapter.cpp` 与各自 codec profile 交叉确认。`encodedLength=transmittedLength`，实际码率统一为 `payloadLength/encodedLength`。

- S200：19 个 BCH(15,11,1)，总输入 209 bit，其中 9 bit 为末尾 filler，输出 285 bit。
- B200：BCH(255,207,6) 前置 7 个已知零并缩短，发送 248 bit。
- S300：28 个 BCH(15,11,1)，总输入 308 bit，其中 8 bit 为末尾 filler，输出 420 bit。
- B300：BCH(511,421,10) 缩短 121 bit，发送 390 bit。
- B300-426：BCH(511,385,14) 缩短 85 bit，发送 426 bit。

300 bit 裁定：B300-390 是码率更高的正式主基线；B300-426 是纠错能力更强的正式增强候选。两者都进入 S1 五方案与 S2 八 Case 比较，不能因单条曲线更好而互相替代。第4章正文以 B300-390 说明主设计，以 B300-426 说明“增加36个发送比特换取 t=14”的增强权衡；完整细分曲线可放附录。

注意：S2 Stage02 还派生了 K200 的 BCH(511,421/385) 和 K300 的双块 BCH(255,207) Case。这些是信道实验比较矩阵，不新增核心 codec 身份。
