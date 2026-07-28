# stage07_multipath_validation 验证报告

最终 Gate：`PASS_STAGE07_MULTIPATH_VALIDATION`

## 冻结模型

- `channelModelId=S2_FIXED_REAL_FIR_V1`
- 原始冲激响应 `[1, 0.65, 0, 0.35]`，有效延迟 `[0,1,3]`
- 原始能量 `1.545`，单位能量归一化后能量 `1.0`
- `LINEAR_FULL`、`ZERO_OUTSIDE_FRAME`、观测长度 `N+3`
- 块线性 MMSE：`A=H^T H+sigma2 I`，带状 Cholesky 求解，无显式求逆
- solver residual 容差 `1e-11`

## 实际执行

- MinGW GCC 15.2.0 Release 构建：PASS。
- CTest：1/1 PASS；包含非法维度拒绝、逐帧 AWGN 隔离和同身份复现。
- 7 类固定卷积向量：PASS。
- MATLAB R2024b 独立参考：39 组 PASS。
- C++/MATLAB：33616 行，最大连续差 `2.1316282072803006e-13`，
  hard mismatch `0`。
- `h=[1]`：8 Case 的 received、MMSE 输出、硬判决、payload、错误计数和
  decoder status 全部一致。
- 8 Case 无噪声：每 Case 1007 帧，总计 8056 帧；payload/decoder/
  miscorrection/undetected error 全为 0。
- 最大 solver residual：`2.63252502148031e-16`。
- continuous/resume/shard：全部整数计数完全一致。
- trial：24 点、12000 帧；运行速率约 3884 帧/秒。
- stage08 24 点正式网格在 formal 前人工冻结。
- 结果文件 SHA-256：PASS。

## 失败与修复

首次 C++ 构建发现 stage01/stage02 位向量类型不一致，显式转换后完整重跑。
MATLAB 两次失败分别源于不兼容导入选项和数值经默认字符串格式丢失精度；
没有放宽容差，改为保持原始 double 后独立参考最大差降至 `2.14e-13` 内。

## Git 与范围

- branch：`stage07-08-bch-s2-multipath`
- functional base：`be243bec3672584792c6486766a89b4795aa8cc3`
- functional content：`8934d6b01b0415262c753f10e0044b100bcdc95a`
- 远程分支已验证包含 functional content。
- `main` 未合并。
