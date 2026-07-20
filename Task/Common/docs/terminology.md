# 术语表

| 术语 | 冻结含义 |
|---|---|
| `K_payload` | 原始 payload 长度，也是 BER/FER 唯一统计范围 |
| `K_codec_input` | 实际进入编码器的信息长度，可包含辅助位 |
| `N_encoded` | 最终编码或码率适配后的实际编码长度 |
| `N_transmitted` | 实际进入 BPSK 和信道的比特数 |
| `R` | `K_payload/N_encoded` |
| `noiseGroupId` | 公平对比组标识 |
| `reuseNoiseAcrossSnr` | 跨 SNR 复用同一标准高斯序列，只改变 sigma |
| `BER` | payload 错误 bit 数除以 payload 总 bit 数 |
| `FER` | payload 错误帧数除以总帧数 |
| `payloadSuccessRate` | `1-FER` |
| `decoderDeclaredSuccessRate` | 译码器自行声明成功的比例 |
| `undetectedErrorRate` | 译码器声明成功但 payload 错误的帧比例 |
| `point_results.csv` | 每个 SNR 点一行的点级结果 |
| `curve_summary.csv` | 每条曲线一行的曲线级结果 |
| `codingGain_dB` | 曲线级编码增益，不是点级直接测量值 |
| `trace.csv` | 中间过程追踪表 |
| `checkpoint` | 长运行保存点，本阶段只冻结字段 |

