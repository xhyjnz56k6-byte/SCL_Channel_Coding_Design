# 已知问题

- `EXACT_FROM_TYPE_AND_COUNT` 不包含 STL 分配器、堆块头和对齐的实现相关开销。
- 最大工作区为当前数据结构 capacity 推导，不是操作系统级峰值 RSS。
