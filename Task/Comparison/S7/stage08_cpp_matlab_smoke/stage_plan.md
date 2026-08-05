# Stage08 C++/MATLAB Smoke 计划

比较映射、hash、置换、pair、BPSK、burst mask、AWGN、硬判、LLR、BCH 编码/syndrome/lookup/payload、CC state/output/tie/traceback/payload。

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate 条件 |
|---|---|---|---|---|
| 映射 | mapping_vectors | MATLAB 独立生成 | hash/index mismatch | 全候选一致 |
| 信道 | channel_vector | 公式复算 | 浮点超差 | abs error 达标 |
| BCH | codec/syndrome | 独立 reference | bit/lookup mismatch | 全部一致 |
| CC | trellis/codec | poly2trellis/显式 Viterbi | tie/终态不同 | 全部一致 |

