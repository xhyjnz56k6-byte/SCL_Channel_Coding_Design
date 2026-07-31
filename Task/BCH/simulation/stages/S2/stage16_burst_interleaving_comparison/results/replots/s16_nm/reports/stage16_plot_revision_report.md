# Stage16 plot revision report

## 原图问题

原 4 张总图同时混合无突发、无交织突发和交织突发系列，系列较多；旧绘图层还为 log 坐标将 BER/FER=0 替换为 0.5/denominator，导致高 SNR 区间出现人为 error floor 平台痕迹。部分重合曲线在视觉上也容易让审阅者误以为系列缺失。

## 本次输出

- s16_nm_k200_ber_overview.png：200比特BCH突发信道适应性 / BER
- s16_nm_k200_fer_overview.png：200比特BCH突发信道适应性 / FER
- s16_nm_k300_ber_overview.png：300比特BCH突发信道适应性 / BER
- s16_nm_k300_fer_overview.png：300比特BCH突发信道适应性 / FER

总图：
- s16_nm_k200_ber_overview.png
- s16_nm_k200_fer_overview.png
- s16_nm_k300_ber_overview.png
- s16_nm_k300_fer_overview.png

仅突发对比图：

## 系列完整性

- s16_nm_k200_ber_overview: expected=12, rendered=12
- s16_nm_k200_fer_overview: expected=12, rendered=12
- s16_nm_k300_ber_overview: expected=12, rendered=12
- s16_nm_k300_fer_overview: expected=12, rendered=12

所有 overview 图均审计到 12 个 seriesLabel；所有 burst_only 图均审计到 8 个 seriesLabel。未因曲线重合、视觉相近或图例拥挤合并/省略任何系列。

## 0 值处理与截断

raw figure-data 保留原始复算值，包括 0；publication figure-data 和发布 PNG 移除所有 BER/FER=0 的点，不使用任何 zero surrogate。

- s16_nm_k200_ber_overview / 分块-无突发: 19 个 0 点被移除，publication 曲线终止于 SNR=8.5
- s16_nm_k200_ber_overview / 分块-交织突发: 14 个 0 点被移除，publication 曲线终止于 SNR=11
- s16_nm_k200_ber_overview / 255整块-无突发: 25 个 0 点被移除，publication 曲线终止于 SNR=5.5
- s16_nm_k200_ber_overview / 421整块-无突发: 27 个 0 点被移除，publication 曲线终止于 SNR=4.5
- s16_nm_k200_ber_overview / 385整块-无突发: 28 个 0 点被移除，publication 曲线终止于 SNR=4
- s16_nm_k200_ber_overview / 385整块-无交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k200_ber_overview / 385整块-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k200_fer_overview / 分块-无突发: 19 个 0 点被移除，publication 曲线终止于 SNR=8.5
- s16_nm_k200_fer_overview / 分块-交织突发: 14 个 0 点被移除，publication 曲线终止于 SNR=11
- s16_nm_k200_fer_overview / 255整块-无突发: 25 个 0 点被移除，publication 曲线终止于 SNR=5.5
- s16_nm_k200_fer_overview / 421整块-无突发: 27 个 0 点被移除，publication 曲线终止于 SNR=4.5
- s16_nm_k200_fer_overview / 385整块-无突发: 28 个 0 点被移除，publication 曲线终止于 SNR=4
- s16_nm_k200_fer_overview / 385整块-无交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k200_fer_overview / 385整块-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_ber_overview / 分块300-无突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_ber_overview / 分块300-交织突发: 14 个 0 点被移除，publication 曲线终止于 SNR=11
- s16_nm_k300_ber_overview / 255双块300-无突发: 26 个 0 点被移除，publication 曲线终止于 SNR=5
- s16_nm_k300_ber_overview / 255双块300-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_ber_overview / 421整块300-无突发: 26 个 0 点被移除，publication 曲线终止于 SNR=5
- s16_nm_k300_ber_overview / 421整块300-无交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_ber_overview / 421整块300-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_ber_overview / 385整块300-无突发: 27 个 0 点被移除，publication 曲线终止于 SNR=4.5
- s16_nm_k300_ber_overview / 385整块300-无交织突发: 24 个 0 点被移除，publication 曲线终止于 SNR=6
- s16_nm_k300_ber_overview / 385整块300-交织突发: 24 个 0 点被移除，publication 曲线终止于 SNR=6
- s16_nm_k300_fer_overview / 分块300-无突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_fer_overview / 分块300-交织突发: 14 个 0 点被移除，publication 曲线终止于 SNR=11
- s16_nm_k300_fer_overview / 255双块300-无突发: 26 个 0 点被移除，publication 曲线终止于 SNR=5
- s16_nm_k300_fer_overview / 255双块300-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_fer_overview / 421整块300-无突发: 26 个 0 点被移除，publication 曲线终止于 SNR=5
- s16_nm_k300_fer_overview / 421整块300-无交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_fer_overview / 421整块300-交织突发: 20 个 0 点被移除，publication 曲线终止于 SNR=8
- s16_nm_k300_fer_overview / 385整块300-无突发: 27 个 0 点被移除，publication 曲线终止于 SNR=4.5
- s16_nm_k300_fer_overview / 385整块300-无交织突发: 24 个 0 点被移除，publication 曲线终止于 SNR=6
- s16_nm_k300_fer_overview / 385整块300-交织突发: 24 个 0 点被移除，publication 曲线终止于 SNR=6

因此曲线会自然终止在最后一个严格大于 0 的观测点，高 SNR 区域不再保留人为水平平台。

## 数据与仿真边界

原始统计是否被修改：否。

本次是否重跑仿真：否。

本次仅基于 Stage16 已存在的 formal raw CSV 复算 BER/FER 并重绘。新图更适合论文/汇报展示，因为它保留完整系列审计，同时去掉了 0 值替代造成的视觉误导，并额外提供了仅突发对比视图。

## figure-data 行数

- s16_nm_k200_ber_overview: raw=444, publication=291
- s16_nm_k200_fer_overview: raw=444, publication=291
- s16_nm_k300_ber_overview: raw=444, publication=223
- s16_nm_k300_fer_overview: raw=444, publication=223
