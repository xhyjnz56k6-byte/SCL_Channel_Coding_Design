# S7 LDPC 无交织近码率基线来源审计

- 选择：`LDPC_BG2_K300_N640 / DIRECT_LAYERED_NMS / alpha=0.80 / maxIterations=32`。
- 角色：`NO_INTERLEAVING_NEAR_RATE_REFERENCE`；不参与交织推荐排名。
- payload：LDPC=300，CC=300，完全匹配。
- 码率：LDPC=300/640=0.468750000000；CC=300/612=0.490196078431。
- 码率差：absolute=0.021446078431；relative=4.375000%。
- 信道：LDPC 仅有无突发 BPSK+AWGN；没有 2%/5%/10% 连续极性反转数据。
- SNR：两者均为 Es/N0，sigmaSquared=1/(2*10^(EsN0Db/10))，无需转换。
- BER：两者均以原始 300-bit payload 为统计对象。
- FER：两者均在 payload 至少存在一个错误 bit 时记为 1。
- 时延：两者均用 steady_clock 只包围译码函数，可作软件实现 CPU 时间参考；跨实现结果不等价于硬件复杂度。
- 复杂度：LDPC 有迭代、边更新和分类操作量；CC 有固定 306 trellis steps/64 states。二者没有统一 operation-count 口径，不合并为单一数值排名。
- 插值/平滑/合成：NO/NO/NO；摘录 31 个原始行。
- Formal rerun：S7 BCH=NO，S7 CC=NO，LDPC=NO。
- 原始 LDPC 工程：READ ONLY；本轮开始前已有 23 个 readme 修改，使用状态与哈希前后相等证明本轮未修改。
