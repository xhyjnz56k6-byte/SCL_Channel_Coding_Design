# 卷积码 S3 五个核心问题回答

## 问题1：1/2、2/3、3/4 的可靠性与吞吐如何权衡
### 使用的数据
`stage09_two_level_merged_point_results.csv`: FER, BER, actualRate, normalizedGoodput。
### 参考图
`stage09_two_level_fer.png`, `stage09_two_level_goodput.png`。
### 数据现象
低码率通常 FER 更低，高码率 actualRate 更高；normalizedGoodput 按 actualRate*(1-FER) 计算。
### 结论
可靠性优先选 R12，吞吐优先在目标 FER 可接受时选 R23/R34。
### 适用条件
300 bit、符号级离散 BPSK-AWGN、SNR=Es/N0。
### 限制
不能外推到连续时间波形信道。

## 问题2：硬判决、浮点软判决和量化软判决如何权衡
### 使用的数据
`stage09_two_level_gain_summary.csv`, `stage11_soft_quantization_results.csv`。
### 参考图
`stage09_two_level_hard_soft_fer.png`, `stage11_quantization_fer.png`。
### 数据现象
软判决相对硬判决在目标 FER 附近有 SNR 收益；Q6 是本轮满足 Gate 的量化推荐。
### 结论
性能优先用浮点软判决，工程存储优先可选 Q6。
### 适用条件
当前 clipMax=2、零饱和/溢出 Gate。
### 限制
未覆盖其它调制或硬件量化器。

## 问题3：整块零尾与按时隙连续编码谁更适合高速业务
### 使用的数据
`stage14_block_continuous_results.csv`。
### 参考图
`stage14_first_output_latency.png`, `stage14_goodput.png`。
### 数据现象
连续方案避免重复尾比特，首次输出时延低于整块完成等待。
### 结论
高速流式业务优先考虑连续组织，slot 长度是业务候选参数。
### 适用条件
50x6/100x3/150x2 三种 300 bit 切分。
### 限制
没有真实符号率，时延单位是归一化符号。

## 问题4：完整块、固定回溯和真滑窗如何权衡
### 使用的数据
`stage10_traceback_study_results.csv`, `stage13_sliding_window_results.csv`。
### 参考图
`stage10_traceback_memory.png`, `stage13_latency_reliability_tradeoff.png`。
### 数据现象
有限回溯和滑窗降低缓存/首次输出等待，但可能带来相对 full mismatch。
### 结论
可靠性优先 full，均衡配置参考 Dtb=84 与 W96/S25/D70。
### 适用条件
当前 300 bit 零尾终止模型。
### 限制
CPU 时间为软件测量，非硬件周期。

## 问题5：量化位宽、回溯深度、窗口长度和步长怎样配置
### 使用的数据
`stage10_traceback_recommendation.csv`, `stage11_quantization_recommendation.csv`, `stage13_window_prescan.csv`。
### 参考图
Stage10/11/13 对应参数扫描图。
### 数据现象
Q6 满足量化 Gate；Dtb=84 在扩展候选中达到 preferred；W/S/D 需要按 FER 与时延共同筛选。
### 结论
balanced 建议 Q6、Dtb=84、W96/S25/D70 作为后续候选。
### 适用条件
仅限本轮仿真参数。
### 限制
Stage09 完整粗网格仍需补齐后再做最终不可逆结论。
