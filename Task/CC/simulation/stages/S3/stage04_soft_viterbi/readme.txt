阶段：Stage04 - 浮点软判决 Viterbi

目的：建立接收符号/软信息驱动的整块软判决 Viterbi，作为高速电文推荐方案的性能基准。

作用：采用平方欧氏距离分支度量、64 状态 ACS、确定性 tie-break 和零终止回溯。Hard 与 Soft 从同一接收符号派生，确保性能增益不来自不同噪声样本。

得到的结果：无噪声、低噪声、NaN/Inf 拒绝以及 MATLAB vitdec 非量化软判决对照全部通过，Gate 为 PASS_STAGE04_CC_SOFT_VITERBI。

主要文件：scripts/build_and_test_stage04.py 是测试入口；matlab/stage04_matlab_reference.m 是独立参考；results/stage04_soft_viterbi_cpp_matlab_vectors.csv 和 results/stage04_soft_viterbi_matlab_comparison.csv 为对照结果。

交付关系：该实现被 Stage09、Stage11、Stage14、Stage15 的 Soft 结果复用；本阶段结果主要作为正确性证据。
