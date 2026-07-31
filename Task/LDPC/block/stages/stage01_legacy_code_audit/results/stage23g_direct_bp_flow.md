# Stage23g Direct BP

Stage23g 直接展开 BG2 子矩阵，预计算 Hp 高斯消元变换；译码按 base layer、展开 row 顺序更新。
每条消息使用 `2*atanh(product(tanh(q/2)))`，atanh 输入限于 `±(1-1e-16)`；每次完整迭代后计算 syndrome 并提前停止。
正式结果字段明确记录 `directOnly=true, rateMatchExecuted=false, rateRecoverExecuted=false`。
