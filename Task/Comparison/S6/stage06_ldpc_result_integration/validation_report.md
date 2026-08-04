# Stage06 验证报告

- N560 元数据：K=300、N=560、Zc=56、filler=148、parity=112、rankH=112：PASS
- BP/NMS：各 31 点，31/31 成对
- payload/codeword/LLR 哈希逐对相同：PASS
- 共用 syndrome full-iteration early-stop：PASS
- maxIter=32；NMS alpha=0.95：PASS
- NaN/Inf：0
- 复杂度、存储、时延、valid/invalid 四象限字段完整：PASS
- 10/20/30 Formal：未运行

Gate：`PASS_LDPC_N560_RESULT_INTEGRATION`
