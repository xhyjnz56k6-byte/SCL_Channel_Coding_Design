# Stage13 突发错误与交织基础验证报告

- 分支：`stage13-16-bch-s2-burst-interleaving`
- 基线：`8bd58cf80c60f2d373d479b9d8e02a1919fdca8d`
- 内容提交：`将在本地功能提交后冻结`
- 8 个 Case：全部与 Stage02 contract 一致
- 固定向量：96
- 预扫点：1664
- 预扫帧：332800
- 确定性验证帧（连续/resume/shard/重复）：4800
- MATLAB/C++ mismatch：0
- checkpoint/resume：整数统计完全一致
- shard/merge/逆序执行：整数统计完全一致
- Stage14 冻结长度：`{"200": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50], "300": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]}`
- Stage15 方法长度：`{"200": [1, 2, 3, 5, 8, 10, 15, 20, 30], "300": [1, 2, 3, 5, 8, 10, 15, 20, 30]}`
- Stage15 深度长度：`{"200": [3, 5, 8, 10, 15, 20, 30], "300": [3, 5, 8, 10, 15, 20, 30]}`
- Gate：`PASS_STAGE13_BURST_INTERLEAVING_VALIDATION_FUNCTIONAL`

未实现可选的 `CONVOLUTIONAL_EXTENSION`；它不属于四种必需交织器和正式 Gate。
