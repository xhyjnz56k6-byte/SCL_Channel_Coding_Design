# 噪声策略

CC 使用 `generateStandardGaussianFrame(noiseSeed, noiseGroup, frameIndex, transmittedBits)`。
LDPC 复用同一 seed 常量和按 frame 生成策略；同一 case/SNR/frame 的 BP 与全部 NMS alpha 共享唯一 channelLlr。
