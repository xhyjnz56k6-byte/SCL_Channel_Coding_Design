# 配对 runner

每个 Case×SNR×frame 只生成一次 payload、码字、标准高斯噪声、接收符号和 channelLlr，随后依次传给 BP 与所有 NMS alpha。哈希字段一致，禁止译码器内部生成噪声。
