# Stage02 Trellis 与编码器计划

## 目标

实现与 `poly2trellis(7,[171 133])` 对齐的 64×2 trellis、连续编码状态接口和 300 bit 整块零尾编码器。

## 范围

允许修改：

```text
Task/CC/shared/**
Task/CC/block/current/**
Task/CC/simulation/stages/S3/stage02_trellis_encoder/**
```

禁止修改 `Task/Common/**`、`Task/BCH/**`、`Task/LDPC/**` 和 Stage01 功能内容。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 64×2 trellis | `shared/` | 全状态、全输入遍历 | 非法 state/input 拒绝 | 转移确定且已知向量一致 |
| 171/133 输出 | `shared/` | 独立移位寄存器参考 | bit 顺序反转对比 | C++ mismatch=0 |
| 连续编码状态 | `block/current/` | 分段拼接与一次编码相同 | 非二进制输入拒绝 | 输出与状态一致 |
| 300 bit 零尾 | `block/current/` | 随机 100 帧、全零/全一/脉冲 | 长度不变量 | 612 bit 且 final state=0 |
| MATLAB 对比 | `matlab/` | `poly2trellis`、`convenc` | mismatch 触发错误 | bitMismatch=0 |

## Gate

```text
PASS_STAGE02_CC_TRELLIS_ENCODER
```

只有 Release build、CTest、C++ 独立参考和 MATLAB 对比全部实际通过后才能声明。
