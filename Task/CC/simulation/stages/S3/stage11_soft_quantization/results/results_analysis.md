# Stage11 软判决量化复核 results 分析

## 1. 阶段实验目的
支撑 CC S3 300 bit 高速电文正式评估，输出可追溯的性能和资源数据。

## 2. 本轮正式配置
SNR = Es/N0，-5.0 dB 到 10.0 dB，步长 0.5 dB；minFrames=1000，targetFrameErrors=200，maxFrames=50000。

## 3. 仿真规模
正式结果行数 931，累计帧数 19379409，配置组合数 21。

## 4. 数据完整性检查
本轮结果由脚本从正式 CSV 和 runtime shard 生成，未手工修改 BER/FER，未用空图作为 PASS。

## 5. 主要现象
Float 与 Q3-Q8 量化结果用于 Stage15 的量化损失和 Q8 工程候选。

## 6. 结果图

### stage11_quantization_latency.png
![stage11_quantization_latency](./stage11_quantization_latency.png)
对应 figure-data：stage11_quantization_latency_figure_data.csv。

### stage11_quantization_memory.png
![stage11_quantization_memory](./stage11_quantization_memory.png)
对应 figure-data：stage11_quantization_memory_figure_data.csv。

### stage11_quantization_snr_loss.png
![stage11_quantization_snr_loss](./stage11_quantization_snr_loss.png)
对应 figure-data：stage11_quantization_snr_loss_figure_data.csv。

### stage11_quantization_true_clip.png
![stage11_quantization_true_clip](./stage11_quantization_true_clip.png)
对应 figure-data：stage11_quantization_true_clip_figure_data.csv。

### stage11_r12_quantization_ber.png
![stage11_r12_quantization_ber](./stage11_r12_quantization_ber.png)
对应 figure-data：stage11_r12_quantization_ber_figure_data.csv。

### stage11_r12_quantization_fer.png
![stage11_r12_quantization_fer](./stage11_r12_quantization_fer.png)
对应 figure-data：stage11_r12_quantization_fer_figure_data.csv。

### stage11_r12_representative_fer.png
![stage11_r12_representative_fer](./stage11_r12_representative_fer.png)
对应 figure-data：stage11_r12_representative_fer_figure_data.csv。

### stage11_r23_quantization_ber.png
![stage11_r23_quantization_ber](./stage11_r23_quantization_ber.png)
对应 figure-data：stage11_r23_quantization_ber_figure_data.csv。

### stage11_r23_quantization_fer.png
![stage11_r23_quantization_fer](./stage11_r23_quantization_fer.png)
对应 figure-data：stage11_r23_quantization_fer_figure_data.csv。

### stage11_r23_representative_fer.png
![stage11_r23_representative_fer](./stage11_r23_representative_fer.png)
对应 figure-data：stage11_r23_representative_fer_figure_data.csv。

### stage11_r34_quantization_ber.png
![stage11_r34_quantization_ber](./stage11_r34_quantization_ber.png)
对应 figure-data：stage11_r34_quantization_ber_figure_data.csv。

### stage11_r34_quantization_fer.png
![stage11_r34_quantization_fer](./stage11_r34_quantization_fer.png)
对应 figure-data：stage11_r34_quantization_fer_figure_data.csv。

### stage11_r34_representative_fer.png
![stage11_r34_representative_fer](./stage11_r34_representative_fer.png)
对应 figure-data：stage11_r34_representative_fer_figure_data.csv。

## 7. 限制
CPU 时间依赖当前硬件和进程并行状态；零误码点只代表有限帧数下的上界，不代表理论误码平台。