# CC Viterbi 度量定义

## 硬判决分支度量

未打孔母码的硬判决分支度量为观测 bit 与候选 `[g1,g2]` 的汉明距离：

```text
branchMetricHard =
    observedMask[0] * (hardBit[0] != g1) +
    observedMask[1] * (hardBit[1] != g2)
```

`observedMask=false` 的缺失位不参与度量，禁止把打孔缺失位当作真实 0 或 1。

## 浮点软判决分支度量

第一版正式浮点基准使用接收符号欧氏距离：

```text
x(0) = +1
x(1) = -1

branchMetricSoft =
    observedMask[0] * (received[0] - x(g1))^2 +
    observedMask[1] * (received[1] - x(g2))^2
```

允许使用数学上严格等价、不会改变 ACS 排序的 LLR 负对数似然度量，但实现必须记录所用形式。软去打孔的中性 LLR 为 0；若使用 received-symbol 欧氏形式，则必须以 mask 排除缺失位，不能把占位数值参与平方距离。

## 初始化和终止

- 时刻 0 只有 state 0 的路径度量为 0。
- 其他 63 个状态使用安全有限哨兵 `INF`，其值必须留有累加余量。
- 整块零尾译码强制从最终 state 0 回溯。
- 连续/滑窗模式的终止策略由对应 Stage 冻结，不得误用整块零尾假设。

## ACS tie-breaking

所有实现使用同一确定性规则：

1. 较小累积路径度量胜出；
2. 度量完全相等时，较小的 predecessor state index 胜出；
3. predecessor 仍相同时，较小 input bit 胜出。

浮点相等按实际比较值判断，不引入随 SNR 改变的模糊 epsilon。测试必须构造精确 tie 并验证重复运行输出一致。

## 路径度量归一化

每个 trellis 输入时刻完成全部 64 状态 ACS 后：

1. 在可达状态中求最小有限路径度量；
2. 所有可达状态减去该最小值；
3. 不可达状态保持 `INF`；
4. 若不存在有限路径，立即报告 `ERROR_ABORT`；
5. 任意 NaN、Inf（浮点实际值）或整数溢出计数非零时，Gate 失败。

归一化仅减去所有候选共有的常数，不改变幸存路径选择。

## 幸存路径

每个 trellis 时刻、每个可达状态至少保存：

```text
predecessorState
inputBit
```

整块译码保存 306 个时刻所需的完整幸存信息。Stage10 和 Stage13 可研究有限回溯或环形缓存，但不得改变本合同的 tie-breaking。

## 去打孔中性语义

- soft LLR：缺失位置写 0，且 mask=false；
- soft received-symbol：占位值仅用于保持索引，mask=false 时不参与度量；
- hard：缺失位置的占位 bit 无语义，必须由 mask=false 排除；
- `observedMask` 的长度必须与恢复后的 `N_mother` 相同；
- 实际消耗的观测数量必须恰好等于 `N_transmitted`。
