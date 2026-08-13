阶段：Stage03 - 硬判决 Viterbi

目的：建立基于解调后 0/1 比特的整块硬判决 Viterbi 基线。

作用：使用汉明距离分支度量、64 状态 ACS、确定性 tie-break 和已知零终止全回溯。其结果是后续 Hard/Soft 性能公平比较中的硬判决参考。

得到的结果：无噪声、固定错误和 MATLAB vitdec 硬判决参考均逐比特一致，Gate 为 PASS_STAGE03_CC_HARD_VITERBI。该阶段证明硬判决译码链路正确，不代表 AWGN 下的正式性能结论。

主要文件：scripts/build_and_test_stage03.py 运行构建和回归；matlab/stage03_matlab_reference.m 提供 MATLAB 对照；results/stage03_hard_viterbi_cpp_matlab_vectors.csv 与 results/stage03_hard_viterbi_matlab_comparison.csv 是验证证据。

交付关系：供 Stage09、Stage14、Stage15 的 Hard 曲线使用；通常不需单独上传给老师。
