# Stage11 量化实现核验

核验源：`stage11_soft_quantization_runner.cpp`、`stage11_clip_selection.csv`、`stage11_soft_quantization_results.csv`。

- Q3--Q8 的数字是包含符号位的总位宽；$q_{max}=2^{b-1}-1$，采用对称整数区间 $[-q_{max},q_{max}]$。
- 输入是解打孔后的实值接收样值。裁剪幅度 Q3--Q6 为 1.5，Q7--Q8 为 2.0，量化步长为裁剪幅度除以 $q_{max}$。
- 量化先执行 `std::lround(received/step)`，再饱和到对称整数区间；不是截断。
- 量化译码支路的分支度量为整数平方欧氏距离，路径累计量为 `int32_t`；不是“只量化输入而路径度量保持浮点”。
- 候选累计用 `int64_t` 临时量，超过 `int32_t` 或 $10^9$ 上限时饱和；每步减去当前最小路径度量进行归一化。
- 正式结果中 `integerOverflowCount` 与 `pathMetricSaturationCount` 对全部模式、码率和信噪比求和均为 0。
