# Stage05 主突发信道计划

主信道顺序固定为 BPSK→连续极性反转→AWGN，接收机未知，禁止绕回。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 调制后反转 | s7.cpp | 固定符号向量 | 调制前改 bit | received 公式一致 |
| L=0 | unit test | ratio=0 | 非 AWGN 退化 | symbols 不变 |
| 边界 | burst spec | 六位置/全帧 | wrapAround | start/end 合法 |

