# Stage13 验证报告

Gate：`PASS_STAGE13_CC_SLIDING_WINDOW`。base `6601bcd1dff50269d525aa6bf2362dee1eab2bf7`；content `ea54079373ea4cc865e2ea152be8a86094b9ae8f`；未合并 main。

Release build、候选负向检查、hard/soft 无噪声、1000 帧小 AWGN、300 bit 输出索引/决定时间 checker、Stage12 审计回归和 `git diff --check` 均实际通过。选择 window96/slide25/Dtb70。R12 与完整块 mismatch=0；R23 有 77 bit/8 frame mismatch，已按 head/boundary/middle/tail 完整记录，无未解释 mismatch。远程验证延后至 Stage15。
