# Stage13 规格冻结：连续流滑窗 Viterbi

冻结 `tracebackDepthBits=70`；候选 `windowInputBits={64,96,128,192}`、`slideStepBits={25,50,100}`。窗口必须大于 70 且 slide 不大于 window；非法组合必须拒绝。

实现采用 state metric carry：每次只处理新到达的 slide 输入，不重算重叠；survivor 环保存 Dtb，初始 warmup=70，稳定期输出按 slide 批次发布，最终已知零尾从 state0 flush。`outputBitsPerStep` 是本批新决定 payload 数；puncture phase 由 Stage12 连续编码保持。

主验证 R12 soft，扩展 R23 soft；同时必须通过 hard/soft 无噪声。比较区域为 head[0,70)、tail[230,300)、slot boundary±5 bit、其余 middle。

| 需求 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|
| 参数合同 | 合法候选 prescan | window64/slide>window 拒绝 | PASS |
| state metric/survivor carry | 无噪声 hard/soft | 非有限输入拒绝 | PASS |
| 输出完整性 | 300 bit 唯一索引 | 重复/缺失检查 | PASS |
| warmup/flush | decision metadata | warmup 前输出检查 | PASS |
| 与完整块比较 | 固定噪声+小 AWGN | 分区计数检查 | PASS |

Gate：`PASS_STAGE13_CC_SLIDING_WINDOW`
