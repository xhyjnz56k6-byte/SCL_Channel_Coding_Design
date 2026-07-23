# Known issues

- 574,743 帧中有 3 个超纠错能力帧的 C++ 与 MATLAB 官方 decoded payload 不同；这些帧不改变
  frame-error 判定，因此全部点 FER 和配对 frame-error 判定完全一致。最大逐点 BER 绝对差为
  `4.000000000000531e-06`，可追溯到最多 4 bit 的失败 payload 差异。
- BCH-S200 的 FER=1e-3 未被双方实测网格共同夹住，因此按冻结规则不外推，只记录
  `NOT_BRACKETED`。
- 大型共享输入约 1 GiB，不提交 Git；已提交逐文件 SHA-256、格式、种子、噪声策略和可复现命令。
- MATLAB 官方 S200 译码为 19 个 BCH(15,11) 子块，单进程较慢；正式结果使用 4 个独立
  MATLAB 进程按 SNR 点并行，点内算法、输入和计数定义未改变。

- ??????? C++ ? MATLAB Official ????????????????????????????????
