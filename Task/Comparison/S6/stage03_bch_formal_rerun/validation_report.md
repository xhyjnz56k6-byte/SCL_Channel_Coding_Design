# Stage03 验证报告

- Release、单线程、100 帧预热、无逐帧日志：PASS
- Smoke：S200/B200 各 1000 帧，PASS
- Formal：2×31=62 点，Es/N0=-5:0.5:10 dB，PASS
- processedFrames 范围 1000～50000，停止原因一致：PASS
- 噪声方差公式误差 <=1e-12：PASS
- NaN/Inf：0
- 复杂度：62×33=2046 行，total/average/P95/maximum 完整
- 内存：62 行、分类字段完整，方法 `EXACT_FROM_TYPE_AND_COUNT`
- 环境 JSON/TXT 与 executable SHA256：PASS

Gate：`PASS_BCH_FORMAL_GRID`
