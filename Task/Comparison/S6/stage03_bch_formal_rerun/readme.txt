阶段名称：stage03_bch_formal_rerun

实验目的：在 Release、单线程、受控配置下按 Es/N0 正式重跑 BCH-S200 与 BCH-B200。
主要输入：200 bit 载荷；S200 N=285；B200 N=248；BPSK+AWGN；Es/N0=-5:0.5:10 dB。
完成内容：已完成正式驱动、环境采集、Smoke 和 62 点正式重跑；内存峰值修复前结果已归档。
主要输出：bch_formal_results.csv、bch_complexity_results.csv、execution_environment.json/txt。
当前结论：S200/B200 各 31 点完整，公式、停止条件、复杂度、内存、时延和环境 Gate 通过。
已知问题：电源方案为“平衡”，已如实记录；最大时延仅为平台观测值。
阶段状态：PASS
