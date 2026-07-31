# Stage14 整块与时隙连续组织比较 results 分析

## 1. 阶段实验目的
支撑 CC S3 300 bit 高速电文正式评估，输出可追溯的性能和资源数据。

## 2. 本轮正式配置
SNR = Es/N0，-5.0 dB 到 10.0 dB，步长 0.5 dB；minFrames=1000，targetFrameErrors=200，maxFrames=50000。

## 3. 仿真规模
正式结果行数 372，累计帧数 10491676，配置组合数 12。

## 4. 数据完整性检查
本轮结果由脚本从正式 CSV 和 runtime shard 生成，未手工修改 BER/FER，未用空图作为 PASS。

## 5. 主要现象
Block300、50x6、100x3、150x2 共 12 个正式组织/码率组合。

## 6. 结果图

### stage14_r12_ber.png
![stage14_r12_ber](./stage14_r12_ber.png)
对应 figure-data：stage14_r12_ber.csv。

### stage14_r12_boundary_relative_ber.png
![stage14_r12_boundary_relative_ber](./stage14_r12_boundary_relative_ber.png)
对应 figure-data：stage14_r12_boundary_relative_ber.csv。

### stage14_r12_decision_latency.png
![stage14_r12_decision_latency](./stage14_r12_decision_latency.png)
对应 figure-data：stage14_r12_decision_latency.csv。

### stage14_r12_fer.png
![stage14_r12_fer](./stage14_r12_fer.png)
对应 figure-data：stage14_r12_fer.csv。

### stage14_r12_first_output_latency.png
![stage14_r12_first_output_latency](./stage14_r12_first_output_latency.png)
对应 figure-data：stage14_r12_first_output_latency.csv。

### stage14_r12_normalized_goodput.png
![stage14_r12_normalized_goodput](./stage14_r12_normalized_goodput.png)
对应 figure-data：stage14_r12_normalized_goodput.csv。

### stage14_r23_ber.png
![stage14_r23_ber](./stage14_r23_ber.png)
对应 figure-data：stage14_r23_ber.csv。

### stage14_r23_boundary_relative_ber.png
![stage14_r23_boundary_relative_ber](./stage14_r23_boundary_relative_ber.png)
对应 figure-data：stage14_r23_boundary_relative_ber.csv。

### stage14_r23_decision_latency.png
![stage14_r23_decision_latency](./stage14_r23_decision_latency.png)
对应 figure-data：stage14_r23_decision_latency.csv。

### stage14_r23_fer.png
![stage14_r23_fer](./stage14_r23_fer.png)
对应 figure-data：stage14_r23_fer.csv。

### stage14_r23_first_output_latency.png
![stage14_r23_first_output_latency](./stage14_r23_first_output_latency.png)
对应 figure-data：stage14_r23_first_output_latency.csv。

### stage14_r23_normalized_goodput.png
![stage14_r23_normalized_goodput](./stage14_r23_normalized_goodput.png)
对应 figure-data：stage14_r23_normalized_goodput.csv。

### stage14_r34_ber.png
![stage14_r34_ber](./stage14_r34_ber.png)
对应 figure-data：stage14_r34_ber.csv。

### stage14_r34_boundary_relative_ber.png
![stage14_r34_boundary_relative_ber](./stage14_r34_boundary_relative_ber.png)
对应 figure-data：stage14_r34_boundary_relative_ber.csv。

### stage14_r34_decision_latency.png
![stage14_r34_decision_latency](./stage14_r34_decision_latency.png)
对应 figure-data：stage14_r34_decision_latency.csv。

### stage14_r34_fer.png
![stage14_r34_fer](./stage14_r34_fer.png)
对应 figure-data：stage14_r34_fer.csv。

### stage14_r34_first_output_latency.png
![stage14_r34_first_output_latency](./stage14_r34_first_output_latency.png)
对应 figure-data：stage14_r34_first_output_latency.csv。

### stage14_r34_normalized_goodput.png
![stage14_r34_normalized_goodput](./stage14_r34_normalized_goodput.png)
对应 figure-data：stage14_r34_normalized_goodput.csv。

## 7. 限制
CPU 时间依赖当前硬件和进程并行状态；零误码点只代表有限帧数下的上界，不代表理论误码平台。