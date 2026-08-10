阶段：Stage02 - Trellis 与卷积编码器

目的：实现 S3 的基础编码器和 64 状态 Trellis，并保证其与 MATLAB 通信工具箱的定义一致。

作用：完成 K=7、G1=171(oct)、G2=133(oct) 的状态转移、两路输出、连续编码状态接口以及 300 bit 整块零尾编码。它是硬判决、软判决、打孔和滑窗译码的共同发端。

得到的结果：C++ 产生的 Trellis、编码向量和 MATLAB poly2trellis/convenc 独立参考逐项一致，Gate 为 PASS_STAGE02_CC_TRELLIS_ENCODER。300 bit 零尾整块 R=1/2 的传输长度为 612 bit。

主要文件：matlab/stage02_matlab_reference.m 是独立参考；scripts/build_and_test_stage02.py 负责构建与对照；results/stage02_trellis_encoder_cpp_matlab_vectors.csv 和 results/stage02_trellis_encoder_matlab_comparison.csv 保存对照证据。

交付关系：该阶段的 CSV 是算法正确性附件，不是最终 BER/FER 图的主要上传件。
