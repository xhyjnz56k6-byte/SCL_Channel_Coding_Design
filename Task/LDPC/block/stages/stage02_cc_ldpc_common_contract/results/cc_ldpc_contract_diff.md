# CC/LDPC 契约差异

公共项完全复用 CC Stage14：K=300、BPSK、Es/N0、标准高斯噪声、payload seed、noise seed、BER/FER 原始 payload 口径及 decoder-only 计时。
结构差异仅为编码器、译码器和 transmittedLength；LDPC actualRate 始终为 `300/actualLength`。
