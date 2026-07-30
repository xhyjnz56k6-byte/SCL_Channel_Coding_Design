# 汇总逻辑审计

- BP 与每个候选共享只读 LLR，但每次调用独立初始化 posterior/message/result。
- 每个候选使用独立 `Aggregate`，循环中未复用上一候选计数。
- CSV 直接读取当前返回对象；新增逐帧 hash 与汇总重算一致。
- payload 是 codeword 前 300 位；filler 与 parity 仍参与完整 syndrome。
- 未发现 BP 覆盖 NMS 输出或候选统计串用。
