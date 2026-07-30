# Stage15b NMS 流

Stage15b 正式 runner 外层调用 `rateMatch/rateRecover`，该部分禁止迁移。
只提取旧消息移除、绝对值、first/second minimum、sign product、alpha 缩放、新消息写回和 layered 后验立即更新。
新模块直接消费 Direct Tanner 图和 channel LLR，不链接标准速率匹配接口。
