# Stage12 最终 smoke

六种 Case/decoder 组合均使用独立于 alpha 校准的帧域，BP/NMS 逐帧共享 LLR；NaN/Inf 为零，编码 syndrome 全通过。BER/FER 总体随 Es/N0 下降，零错误点仅作为 smoke 上界，不形成正式编码增益结论。未启动 formal。
