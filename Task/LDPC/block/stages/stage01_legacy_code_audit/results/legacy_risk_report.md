# 风险审计

- Stage19 BG2 `kb<10` 的旧 H 构造不可直接用于 K=300：已由秩感知枚举替代。
- Stage15b runner 含标准速率匹配链路：只迁移 NMS 内核。
- Stage23g maxIterations=16；S4 smoke 明确冻结为 32，early stop 语义保持一致。
- 旧工程始终只读，未写入源码或结果。
