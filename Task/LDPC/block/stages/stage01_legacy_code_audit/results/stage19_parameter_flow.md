# Stage19 参数流

`inputK,targetRate → BG → kb → Zc/setIndex → nb,mb → K_eff,N,M,filler`。
旧 Stage19 的 BG2 `kb<10` H 构造带显式拒绝保护，因此新实现不复用其静态列映射，而是枚举合法 BG2 子矩阵并以 `rankHp==M` 作为编码 Gate。
