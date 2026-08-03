# Fixed-vector Gate clarification

The fixed fixture contains exactly 2,160 scheme/channel/SNR/frame/mode combinations. Only `NO_IMPAIRMENT_NO_NOISE` is required to decode with zero payload errors; impaired cases may contain real decoder errors.

Known blockage is applied in the transmitted-symbol domain after CC puncturing. Every blocked transmitted symbol has neutral LLR 0, and the checker verifies that the neutral-LLR count equals the frozen damage length. A punctured mother-code symbol is not reintroduced by the blockage mask. No-noise metrics remain finite at ±100.

- Identity rows: 720
- Identity errors: 0
- Gate: **PASS**
