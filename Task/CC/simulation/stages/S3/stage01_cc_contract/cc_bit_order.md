# CC 位序与状态编号

## 生成多项式

MATLAB 对齐目标：

```matlab
poly2trellis(7, [171 133])
```

七位二进制展开固定为：

```text
171(oct) = 1111001(bin)
133(oct) = 1011011(bin)
```

寄存器逻辑向量按从新到旧排列：

```text
[u(t), u(t-1), u(t-2), u(t-3), u(t-4), u(t-5), u(t-6)]
```

因此：

```text
g1 = u(t) xor u(t-1) xor u(t-2) xor u(t-3) xor u(t-6)
g2 = u(t) xor u(t-2) xor u(t-3) xor u(t-5) xor u(t-6)
```

分支输出顺序固定为 `[g1, g2]`，母码串行化顺序固定为：

```text
g1(t0), g2(t0), g1(t1), g2(t1), ...
```

## 状态 bit 顺序

状态逻辑向量固定为：

```text
[u(t-1), u(t-2), u(t-3), u(t-4), u(t-5), u(t-6)]
```

`u(t-1)` 是 state index 的 bit 5（MSB），`u(t-6)` 是 bit 0（LSB）：

```text
stateIndex =
    u(t-1)*32 +
    u(t-2)*16 +
    u(t-3)*8 +
    u(t-4)*4 +
    u(t-5)*2 +
    u(t-6)
```

输入 bit 从 MSB 端移入。状态转移：

```text
nextState = ((inputBit & 1) << 5) | (stateIndex >> 1)
```

初始化 state 0 表示六个记忆单元全为 0。

## 分支输出计算

对当前 `stateIndex` 和 `inputBit`：

```text
m1 = (stateIndex >> 5) & 1
m2 = (stateIndex >> 4) & 1
m3 = (stateIndex >> 3) & 1
m4 = (stateIndex >> 2) & 1
m5 = (stateIndex >> 1) & 1
m6 = stateIndex & 1

g1 = inputBit xor m1 xor m2 xor m3 xor m6
g2 = inputBit xor m2 xor m3 xor m5 xor m6
```

冻结的最小已知向量：

| state | input | nextState | g1 | g2 |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 |
| 0 | 1 | 32 | 1 | 1 |
| 32 | 0 | 16 | 1 | 0 |
| 32 | 1 | 48 | 0 | 1 |
| 1 | 0 | 0 | 1 | 1 |
| 1 | 1 | 32 | 0 | 0 |

Stage02 必须构造完整 64×2 表，并用这些向量、MATLAB `poly2trellis` 和 `convenc` 交叉验证。

## 输入和输出顺序

- payload 按容器索引 0 到 `K_payload-1` 依次进入编码器。
- 零尾 6 bit 紧随 payload。
- 译码输出先恢复 306 个 codec-input bit，再删除末尾 6 bit。
- CSV 中 bit 串使用左到右时间顺序，不使用字节内反向显示。
- MATLAB 向量与 C++ `std::vector<uint8_t>` 均按时间从索引 0 向后排列。

## 打孔相位

打孔 mask 的索引基于串行母码 bit 序列，而不是输入时刻：

```text
phase = motherBitIndex % patternLength
```

连续编码时相位跨 slot 保持；只有合同明确的新独立帧才可重置为 0。具体 2/3、3/4 图样在 Stage06 经验证后冻结。
