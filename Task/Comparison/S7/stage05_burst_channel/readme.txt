阶段名称：stage05_burst_channel
实验目的：实现调制后未知连续 BPSK 极性反转并叠加 AWGN。
主要输入：BPSK symbols、母标准高斯样本、sigmaSquared、比例和六位置。
完成内容：burst spec、位置、L=0、全帧反转、不绕回、硬判和 LLR。
主要输出：channel_vector.csv 和单元测试。
当前结论：C++ 与 MATLAB 信道向量一致。
已知问题：擦除和强干扰扩展未做。
阶段状态：PASS

